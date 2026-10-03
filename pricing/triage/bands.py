"""Dated asking bands and a listing-activity liquidity proxy, not sale guarantees."""

from collections import defaultdict
from datetime import datetime
from statistics import median, quantiles

from pricing.knowledge.market import scope_status, valid_positive
from pricing.triage.family_bands import family_name, roll_bucket
from pricing.triage.variants import profile_for, scoped_bucket


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat()
    except AttributeError, ValueError:
        return None


def latest_rows(rows):
    latest = {}
    for row in rows:
        identity = row.get('listing_id')
        if not identity:
            continue
        rank = row.get('observed_at') or '', row.get('listing_updated_at') or ''
        if identity not in latest or rank > latest[identity][0]:
            latest[identity] = rank, row
    return [pair[1] for pair in latest.values()]


def eligible(row):
    return (
        row.get('scope_status') == 'verified'
        and scope_status(row.get('properties', {})) == 'verified'
        and row.get('evidence_kind') == 'ask'
        and row.get('unit_policy') in ('single_item', 'stack_total')
        and type(row.get('amount')) is int
        and row['amount'] > 0
    )


def quantity_bucket(amount):
    return f'quantity:{amount}' if type(amount) is int and amount > 1 else 'name'


def band_for(category, name, rows, *, quantity=1):
    sellers = {}
    priced = []
    for row in rows:
        if row.get('seller_id') and valid_positive(row.get('ask_ist')):
            seller = str(row['seller_id'])
            sellers[seller] = min(sellers.get(seller, float('inf')), row['ask_ist'])
            priced.append(row)
    values = sorted(sellers.values())
    known_dates = [timestamp(r.get('listing_updated_at')) for r in rows]
    dates = sorted(d for d in known_dates if d is not None)[-50:]
    span = (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])).days if dates else None
    recent = all(d is not None for d in known_dates) and span is not None and span < 14
    liquidity = 'none' if len(values) < 3 else 'liquid' if len(values) >= 10 and recent else 'thin'
    observed = sorted(d for r in rows if (d := timestamp(r.get('observed_at'))))
    rune_priced = sum(bool(r.get('prices')) and all(p.get('type') == 'runes' for p in r['prices']) for r in priced)
    return {
        'category': category,
        'name': name,
        'bucket': quantity_bucket(quantity),
        'quantity': quantity,
        'price_unit': 'per item',
        'q1_ist': quantiles(values, n=4, method='inclusive')[0] if len(values) > 1 else values[0] if values else None,
        'median_ist': median(values) if values else None,
        'sellers': len(values),
        'listings': len(rows),
        'priced_listings': len(priced),
        'newest_listing': dates[-1] if dates else None,
        'oldest_listing': dates[0] if dates else None,
        'listing_span_days': span,
        'observed_at': observed[-1] if observed else None,
        'share_priced_in_runes': rune_priced / len(priced) if priced else None,
        'liquidity': liquidity,
        'evidence_kind': 'asks',
    }


def ethereal_bucket(bucket, value):
    suffix = 'yes' if value is True else 'no' if value is False else 'unknown'
    return f'{bucket}|ethereal:{suffix}'


def build_bands(rows, catalog, *, rules=(), policies=()):
    from pricing.triage.adapters import from_listing
    from pricing.triage.engine import matches

    groups = defaultdict(list)
    names = {(r['type'], r['name'], 1) for r in catalog}
    for row in latest_rows(rows):
        key = row.get('category'), row.get('name'), row.get('amount')
        if all(key) and eligible(row):
            names.add(key)
            groups[key].append(row)
    bands = []
    families = defaultdict(list)
    family_specs = {}
    affixed_rules = [r for r in rules if r.get('category') in ('magic', 'rare', 'crafted') and r.get('bucket')]
    for category, name, amount in sorted(names):
        members = groups[(category, name, amount)]
        policy = profile_for({'category': category, 'name': name}, policies)
        facets = policy.get('facets', [])
        separate = not facets and category == 'uniques'
        buckets = {quantity_bucket(amount): members}
        for row in members:
            item = from_listing(row)
            if amount == 1 and item['category'] in ('magic', 'rare', 'crafted'):
                for family_rule in affixed_rules:
                    if matches(item, family_rule):
                        key = family_name(family_rule), roll_bucket(family_rule, item)
                        if key[1] is not None:
                            families[key].append(row)
                            families[(key[0], family_rule['bucket'])].append(row)
                            family_specs[key] = sorted(family_rule['properties'])
            rule = next((r for r in rules if r.get('bucket') and matches(item, r)), None)
            if rule and amount == 1:
                buckets.setdefault(rule['bucket'], []).append(row)
        for bucket, selected in buckets.items():
            band = band_for(category, name, selected, quantity=amount)
            band.update(bucket=bucket, separate_ethereal=separate)
            bands.append(band)
            if facets:
                partitions = defaultdict(list)
                for row in selected:
                    key = scoped_bucket(bucket, from_listing(row), facets)
                    if key is not None:
                        partitions[key].append(row)
                for key, cohort in partitions.items():
                    variant = band_for(category, name, cohort, quantity=amount)
                    variant.update(bucket=key, facets=facets)
                    bands.append(variant)
            if separate:
                for eth in (False, True, None):
                    cohort = [r for r in selected if r.get('ethereal') is eth]
                    if not cohort:
                        continue
                    variant = band_for(category, name, cohort, quantity=amount)
                    variant.update(bucket=ethereal_bucket(bucket, eth), ethereal=eth)
                    bands.append(variant)
    for (name, bucket), members in families.items():
        band = band_for('family', name, members)
        band.update(bucket=bucket, roll_properties=family_specs.get((name, bucket)))
        bands.append(band)
    return {'schema_version': 1, 'bands': bands}
