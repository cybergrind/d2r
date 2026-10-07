"""Guide-reviewed named roll groups; asking premiums do not establish demand."""

from pricing.triage.bands import band_for, eligible, latest_rows
from pricing.triage.roll_comparisons import numeric


def compile_placements(rows, policies):
    from pricing.triage.adapters import from_listing
    from pricing.triage.engine import matches

    rows = latest_rows(rows)
    compiled = []
    for policy in policies:
        if not policy.get('source'):
            raise ValueError('Named roll placement requires a reviewed guide source')
        groups = {'ordinary': [], 'top': []}
        for row in rows:
            if row.get('category') != policy['category'] or row.get('name', '').casefold() != policy['name'].casefold():
                continue
            if row.get('amount') != 1 or not eligible(row) or not matches(from_listing(row), policy):
                continue
            value = row.get('properties', {}).get(policy['property'])
            if numeric(value) and policy['min'] <= value <= policy['max']:
                groups['ordinary' if value < policy['valuable_min'] else 'top'].append(row)
        bands = {key: band_for(policy['category'], policy['name'], group) for key, group in groups.items()}
        ordinary, top = bands['ordinary'], bands['top']
        if min(ordinary['sellers'], top['sellers']) < 3:
            continue
        if top['median_ist'] < 3 * ordinary['median_ist']:
            continue
        for group, band in bands.items():
            band['bucket'] = f'reviewed-roll:{policy["property"]}:{policy["valuable_min"]}:{group}'
        compiled.append(policy | {'bands': bands})
    return compiled


def lookup(item, placements):
    from pricing.triage.engine import matches

    policy = next((p for p in placements if matches(item, p)), None)
    if policy is None:
        return None
    value = item.get('properties', {}).get(policy['property'])
    if not numeric(value) or not policy['min'] <= value <= policy['max']:
        return {'valid': False, 'reason': f'{policy["label"]} missing or outside native roll range'}
    group = 'ordinary' if value < policy['valuable_min'] else 'top'
    reason = (
        f'{group} roll ({value:g} of {policy["min"]}-{policy["max"]} {policy["label"]}); '
        f'value starts at {policy["valuable_min"]}'
    )
    if group == 'ordinary' and policy.get('alternative'):
        reason += '; value is in ' + policy['alternative']
    return {
        'valid': True,
        'group': group,
        'reason': reason,
        'band': policy['bands'][group],
        'source': policy['source'],
        'ordinary_floor': policy['bands']['ordinary']['median_ist'] <= 1,
    }


def ordinary_has_demand(placement, observation):
    """A buyer or disappearance for the name cannot prove demand for a low roll."""
    group = (observation or {}).get('roll_groups', {}).get(placement['band']['bucket'], {})
    return bool(group.get('buyers', 0) or group.get('uncensored_disappeared', 0))
