"""Material price dimensions: unknown attributes never stand in for a variant."""

import json


def profile_for(item, policies):
    # A named policy overrides a category policy; data remains inspectable and reloadable.
    candidates = [
        p
        for p in policies
        if p.get('category') == item.get('category')
        and ('name' not in p or p['name'].casefold() == str(item.get('name', '')).casefold())
    ]
    return next((p for p in candidates if 'name' in p), next(iter(candidates), {}))


def scoped_bucket(bucket, item, facets):
    values = {}
    for facet in facets:
        value = item.get('properties', {}).get(facet[9:]) if facet.startswith('property:') else item.get(facet)
        if value is None or value == 'unknown':
            return None
        values[facet] = value
    return bucket + '|facets:' + json.dumps(values, sort_keys=True, separators=(',', ':')) if facets else bucket


def socket_bucket(bucket, item):
    """Known and unknown socket variants remain distinct, including fallback bands."""
    if bucket is None:
        return None
    values = [item.get('sockets'), item.get('socket_contents')]
    return bucket + '|sockets:' + json.dumps(values, separators=(',', ':'))


def base_bucket(bucket, item):
    """An upgrade and an unknown base cannot set the original base's price."""
    return None if bucket is None else bucket + '|base:' + json.dumps(item.get('base_code'))
