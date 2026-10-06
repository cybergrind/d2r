"""Family-level paid-property counts, fitted offline without seller leakage."""

import hashlib
import math
from collections import defaultdict

from pricing.triage.paid_facets import FIELDS, conditions, group_key


MIN_CORPUS_ITEMS = 30


def split_sellers(rows, fold=0):
    """Reserve one third of sellers; every copy from a seller stays together."""
    sellers = sorted(
        {str(row['seller_id']) for row in rows if row.get('seller_id') is not None},
        key=lambda seller: hashlib.sha256(seller.encode()).digest(),
    )
    if fold not in (0, 1, 2):
        raise ValueError('Expected one of three seller folds')
    held = set(sellers[fold::3])
    valid = [row for row in rows if row.get('seller_id') is not None]
    return (
        [row for row in valid if str(row['seller_id']) not in held],
        [row for row in valid if str(row['seller_id']) in held],
    )


def reaches(item, key, floor):
    value = item.get('properties', {}).get(key)
    return type(value) in (int, float) and math.isfinite(value) and value >= floor


def score(item, model):
    return sum(reaches(item, key, floor) for key, floor in model['properties'].items())


def paid_set(item, model):
    return {key for key, floor in model['properties'].items() if reaches(item, key, floor)}


def supported_rows(item, model):
    """Require whole training signatures, not interchangeable property counts."""
    found = paid_set(item, model)
    rows = [
        row
        for row in model.get('supporters', [])
        if len(row['paid_properties']) >= model['threshold'] and set(row['paid_properties']) <= found
    ]
    return rows if len({str(row['seller_id']) for row in rows}) >= 3 else []


def lower_quartile(values):
    ordered = sorted(values)
    position = (len(ordered) - 1) / 4
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def fit(listed, corpus, verdicts, *, limit=0.08):
    """Fit one family's floors and smallest safe count against observed drops.

    Callers supply scoped valuable training sellers, one vote per seller, and
    normalized positive non-context properties. Missing rolls never count.
    Common filler is rejected by its prevalence among all family drops.
    """
    if len(corpus) != len(verdicts):
        raise ValueError('Each corpus item needs its baseline verdict')
    values = defaultdict(list)
    for item in listed:
        for key, value in item.get('properties', {}).items():
            if type(value) in (int, float) and math.isfinite(value) and value > 0:
                values[key].append(value)
    floors = {}
    if corpus and listed:
        for key, rolls in values.items():
            if len(rolls) < 3:
                continue
            floor = lower_quartile(rolls)
            market_hits = sum(reaches(item, key, floor) for item in listed)
            drop_hits = sum(reaches(item, key, floor) for item in corpus)
            if market_hits * len(corpus) > drop_hits * len(listed):
                floors[key] = floor
    model = {'properties': floors}
    counts = [score(item, model) for item in corpus]
    baseline = sum(verdict == 'check' for verdict in verdicts)
    threshold, checks = len(floors) + 1, baseline
    for candidate in range(1, len(floors) + 1):
        proposed = baseline + sum(
            count >= candidate and verdict in ('vendor', 'self')
            for count, verdict in zip(counts, verdicts, strict=True)
        )
        if proposed <= len(corpus) * limit:
            threshold, checks = candidate, proposed
            break
    return model | {'threshold': threshold, 'corpus_checks': checks, 'corpus_items': len(corpus)}


def compile_scores(rows, corpus, verdicts, property_ids, keep_ist, *, negatives=(), held_sellers=None):
    """Derive from training sellers only and report untouched seller holdout recall."""
    from pricing.triage.adapters import AFFIXED, from_listing
    from pricing.triage.bands import band_for, eligible, latest_rows, timestamp
    from pricing.triage.learned_patterns import CONTEXT

    grouped = defaultdict(dict)
    for row in latest_rows(rows):
        price = row.get('ask_ist')
        if (
            not eligible(row)
            or row.get('amount') != 1
            or type(price) not in (int, float)
            or not math.isfinite(price)
            or price <= 0
            or row.get('seller_id') is None
            or not timestamp(row.get('observed_at'))
        ):
            continue
        item = from_listing(row)
        if item['category'] not in AFFIXED or not item.get('family'):
            continue
        key = group_key(item)
        if key is None:
            continue
        seller = str(row['seller_id'])
        previous = grouped[key].get(seller)
        if previous is None or price < previous['ask_ist']:
            grouped[key][seller] = row
    models, validation = [], []
    checks = {i for i, verdict in enumerate(verdicts) if verdict == 'check'}
    corpus_keys = [group_key(item) for item in corpus]
    for key, sellers in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        category, family, *facets = key
        if held_sellers is None:
            training, held = split_sellers(list(sellers.values()))
        else:
            training = [row for seller, row in sellers.items() if seller not in held_sellers]
            held = [row for seller, row in sellers.items() if seller in held_sellers]
        training = [row for row in training if row['ask_ist'] >= keep_ist]
        held = [row for row in held if row['ask_ist'] >= keep_ist]
        if len(training) < 3:
            continue
        listed = [from_listing(row) for row in training]
        for item in listed:
            item['properties'] = {
                key: value for key, value in item['properties'].items() if key in property_ids and key not in CONTEXT
            }
        indices = [i for i, item_key in enumerate(corpus_keys) if item_key == key]
        if len(indices) < MIN_CORPUS_ITEMS:
            continue
        model = fit(listed, [corpus[i] for i in indices], [verdicts[i] for i in indices])
        model.update(category=category, family=family, conditions=dict(zip(FIELDS, facets, strict=True)))
        model['supporters'] = [
            {**row, 'paid_properties': sorted(paid_set(item, model))}
            for row, item in zip(training, listed, strict=True)
        ]
        # The specified cap is per rarity, not per family. Allocate it in the
        # same largest-family-first order, including all pre-existing CHECKs.
        total = sum(item['category'] == category for item in corpus)
        baseline = sum(corpus[i]['category'] == category for i in checks)
        model['threshold'] = len(model['properties']) + 1
        added = set()
        # A co-occurring affix is not evidence of standalone demand. Until a
        # model carries reviewed standalone/top-tier evidence, require a pair.
        for threshold in range(2, len(model['properties']) + 1):
            candidate = model | {'threshold': threshold}
            proposed = {
                i for i in indices if verdicts[i] in ('vendor', 'self') and supported_rows(corpus[i], candidate)
            }
            if baseline + len(proposed) <= total * 0.08:
                model['threshold'], added = threshold, proposed
                break
        # Explicit guide false positives veto deployment, never train the holdout.
        veto = any(group_key(item) == key and supported_rows(item, model) for item in negatives)
        if veto:
            model['threshold'] = len(model['properties']) + 1
            added = set()
        checks.update(added)
        model['corpus_checks'] = sum(i in checks for i in indices)
        buckets = defaultdict(list)
        for row, item in zip(training, listed, strict=True):
            buckets[score(item, model)].append(row)
        model['references'] = {
            str(count): band_for(category, family, members) for count, members in buckets.items() if len(members) >= 3
        }
        hits = sum(bool(supported_rows(from_listing(row), model)) for row in held)
        validation.append(
            {
                'category': category,
                'family': family,
                'conditions': model['conditions'],
                'training_sellers': len(training),
                'held_out_sellers': len(held),
                'held_out_flagged': hits,
                'held_out_recall': hits / len(held) if held else None,
                'guide_veto': veto,
                'threshold': model['threshold'],
                'corpus_items': model['corpus_items'],
                'corpus_checks': model['corpus_checks'],
            }
        )
        models.append(model)
    return {'models': models, 'validation': validation}


def lookup(item, models):
    for model in models:
        # Also reject unsafe models in caches built before these guards.
        if model.get('corpus_items', 0) < MIN_CORPUS_ITEMS or model['threshold'] < 2:
            continue
        if (item.get('category'), item.get('family')) != (model['category'], model['family']):
            continue
        if not model.get('conditions') or conditions(item) != model['conditions']:
            continue
        count = score(item, model)
        if count >= model['threshold'] and (rows := supported_rows(item, model)):
            from pricing.triage.bands import band_for

            return {
                'count': count,
                'threshold': model['threshold'],
                'reference_band': band_for(model['category'], model['family'], rows),
                'properties': {key: item['properties'][key] for key in sorted(paid_set(item, model))},
            }
    return None
