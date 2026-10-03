"""Dated asking bands and a listing-activity liquidity proxy, not sale guarantees."""

from collections import defaultdict
from datetime import UTC, datetime
from statistics import median, quantiles

from pricing.knowledge.market import scope_status, valid_positive
from pricing.triage.family_bands import compile_comparisons, family_name, roll_bucket
from pricing.triage.listing_defaults import normalize as listing_defaults
from pricing.triage.variants import base_bucket, profile_for, scoped_bucket, socket_bucket


def instant(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Cache dates without an offset are UTC, independent of the host timezone.
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except AttributeError, ValueError, OverflowError:
        return None


def timestamp(value):
    parsed = instant(value)
    return parsed.date().isoformat() if parsed is not None else None


def latest_rows(rows):
    latest = {}
    for row in rows:
        identity = row.get('listing_id')
        if not identity:
            continue
        rank = tuple(
            instant(row.get(field)) or datetime.min.replace(tzinfo=UTC)
            for field in ('observed_at', 'listing_updated_at')
        )
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
    observed = sorted(d for r in rows if (d := timestamp(r.get('observed_at'))))
    as_of = datetime.fromisoformat(observed[-1]) if observed else None
    active_sellers = {
        str(r['seller_id'])
        for r in priced
        if as_of is not None
        and (updated := timestamp(r.get('listing_updated_at'))) is not None
        and 0 <= (as_of - datetime.fromisoformat(updated)).days <= 14
    }
    liquidity = 'none' if len(values) < 3 else 'liquid' if len(active_sellers) >= 10 else 'thin'
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
        'recent_priced_sellers': len(active_sellers),
        'activity_window_days': 14,
        'evidence_kind': 'asks',
    }


def ethereal_bucket(bucket, value):
    suffix = 'yes' if value is True else 'no' if value is False else 'unknown'
    return f'{bucket}|ethereal:{suffix}'


def build_bands(rows, catalog, *, rules=(), policies=()):
    from pricing.triage.adapters import from_listing
    from pricing.triage.base_comparisons import compile_modifiers
    from pricing.triage.engine import matches

    groups = defaultdict(list)
    names = {(r['type'], r['name'], 1) for r in catalog}
    for row in latest_rows(rows):
        row = listing_defaults(row)
        key = row.get('category'), row.get('name'), row.get('amount')
        if all(key) and eligible(row):
            names.add(key)
            groups[key].append(row)
    bands = []
    families = defaultdict(list)
    family_specs = {}
    affixed_rules = [r for r in rules if r.get('category') in ('magic', 'rare', 'crafted') and r.get('bucket')]
    for category, name, amount in sorted(names):
        members = groups[category, name, amount]
        policy = profile_for({'category': category, 'name': name}, policies)
        facets = policy.get('facets', [])
        separate = not facets and category == 'uniques'
        separate_sockets = category in ('uniques', 'sets')
        buckets = {quantity_bucket(amount): members}
        staffmod_cohorts = defaultdict(list)
        staffmod_rules = (
            [r for r in rules if r.get('bucket') and r.get('category') == category and r.get('name') == name]
            if amount == 1
            and (policy.get('compare_staffmods') or policy.get('compare_modifiers') or policy.get('compare_inherent'))
            else []
        )
        for row in members:
            item = from_listing(row)
            if amount == 1 and item['category'] in ('magic', 'rare', 'crafted'):
                for family_rule in affixed_rules:
                    if matches(item, family_rule):
                        key = family_name(family_rule), roll_bucket(family_rule, item)
                        if key[1] is not None:
                            families[key].append(row)
                            families[key[0], family_rule['bucket']].append(row)
                            family_specs[key] = sorted(family_rule['properties'])
            # Lower rolls belong to the comparison pool even when they do not
            # meet the guide's sell bucket. Facets/skill sets remain partitioned
            # by compile_modifiers; runtime eligibility still uses the full rule.
            for staffmod_rule in staffmod_rules:
                pattern = {
                    **staffmod_rule,
                    **staffmod_rule.get('comparison_pattern', staffmod_rule.get('pattern', {})),
                }
                if matches(item, pattern):
                    staffmod_cohorts[staffmod_rule['bucket']].append(row)
            rule = next((r for r in rules if r.get('bucket') and matches(item, r)), None)
            if rule and amount == 1:
                buckets.setdefault(rule['bucket'], []).append(row)
        for bucket, selected in buckets.items():
            band = band_for(category, name, selected, quantity=amount)
            band.update(
                bucket=bucket,
                separate_ethereal=separate,
                separate_sockets=separate_sockets,
                separate_base=separate_sockets,
            )
            bands.append(band)
            if facets or separate or separate_sockets:
                partitions = defaultdict(list)
                for row in selected:
                    item = from_listing(row)
                    key = ethereal_bucket(bucket, item.get('ethereal')) if separate else bucket
                    key = scoped_bucket(key, item, facets)
                    if separate_sockets:
                        key = base_bucket(socket_bucket(key, item), item)
                    if key is not None:
                        partitions[key].append(row)
                for key, cohort in partitions.items():
                    variant = band_for(category, name, cohort, quantity=amount)
                    variant.update(bucket=key, facets=facets)
                    bands.append(variant)
        for bucket, selected in staffmod_cohorts.items():
            bands.extend(compile_modifiers(category, name, bucket, selected, policy))
    for (name, bucket), members in families.items():
        band = band_for('family', name, members)
        band.update(bucket=bucket, roll_properties=family_specs.get((name, bucket)))
        bands.append(band)
        rule = next((r for r in affixed_rules if family_name(r) == name and r['bucket'] == bucket), None)
        if rule:
            bands.extend(compile_comparisons(rule, members))
    return {'schema_version': 1, 'bands': bands}
