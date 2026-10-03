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
        band = bands.get(('family', name, bucket))
        if band and band.get('median_ist') is not None:
            return band, reference
    return None, reference
