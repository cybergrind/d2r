"""Price matching affixed rolls; retain broader pattern bands as references only."""

from pricing.triage.variants import scoped_bucket


def family_name(rule):
    return str(rule.get('family') or rule.get('name') or '').casefold()


def roll_bucket(rule, item):
    if not rule.get('bucket') or not rule.get('properties'):
        return None
    facets = ['property:' + prop for prop in sorted(rule['properties'])]
    facets += rule.get('band_facets', [])
    return scoped_bucket(rule['bucket'], item, facets)


def comparison_bucket(rule, item):
    prop = rule.get('compare_property')
    value = item.get('properties', {}).get(prop, rule.get('compare_missing'))
    bounds = rule.get('compare_range', {})
    if type(value) not in (int, float) or not bounds.get('min', 1) <= value <= bounds.get('max', 0):
        return None
    facet = rule.get('compare_modifier_facet', 'charm_suffix')
    suffix = item.get(facet)
    if not isinstance(suffix, dict):
        return None
    base = roll_bucket(rule, item | {facet: {k: v for k, v in suffix.items() if k != prop}})
    return f'{base}|no-better:{prop}:{value:g}' if base else None


def compile_comparisons(rule, members):
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import band_for

    if not rule.get('compare_property'):
        return []
    prop = rule['compare_property']
    groups = {}
    for row in members:
        item = from_listing(row)
        if comparison_bucket(rule, item) is None:
            continue
        anchor = item | {'properties': item['properties'] | {prop: rule['compare_range']['min']}}
        groups.setdefault(comparison_bucket(rule, anchor), []).append((row, item))
    bands = []
    for rows in groups.values():
        sample = rows[0][1]
        for value in range(rule['compare_range']['min'], rule['compare_range']['max'] + 1):
            selected = [row for row, item in rows if item['properties'].get(prop, rule.get('compare_missing')) <= value]
            if not selected:
                continue
            target = sample | {'properties': sample['properties'] | {prop: value}}
            band = band_for('family', family_name(rule), selected)
            band.update(
                bucket=comparison_bucket(rule, target),
                comparison={
                    'property': prop,
                    'maximum': value,
                    'label': f'{rule.get("compare_label", prop)} ≤{value}',
                },
            )
            bands.append(band)
    return bands


def lookup(item, rules, bands):
    reference = None
    if item.get('quantity', 1) != 1:
        return None, None
    for rule in rules:
        name = family_name(rule)
        bucket = roll_bucket(rule, item)
        if bucket is None:
            continue
        reference = reference or bands.get(('family', name, rule['bucket']))
        compared = comparison_bucket(rule, item)
        band = bands.get(('family', name, compared)) if compared else None
        band = band or bands.get(('family', name, bucket))
        if band and band.get('median_ist') is not None:
            return band, reference
    return None, reference
