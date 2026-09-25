"""Resolve guide tooltip references into exact cached planner evidence."""

from copy import deepcopy


def resolve_embedded_item(reference, planner, occurrences):
    result = {'reference': deepcopy(reference), 'review_state': 'pending', 'occurrence_ids': []}
    item = planner['items'].get(str(reference['item_id']))
    if item is not None:
        result['item_definition'] = deepcopy(item)
        result['item_locator'] = f'/items/{reference["item_id"]}'
    matches = [
        (i, p)
        for i, p in enumerate(planner['profiles'])
        if reference.get('set_id') is not None and p.get('uid') == reference['set_id']
    ]
    if len(matches) != 1:
        return {**result, 'status': 'missing_set' if not matches else 'ambiguous_set'}
    number, profile = matches[0]
    item = planner['items'].get(str(reference['item_id']))
    if item is None:
        return {**result, 'status': 'missing_item'}
    prefix = f'/profiles/{number}/'
    links = sorted(
        row['id']
        for row in occurrences
        if row['source_locator'].startswith(prefix)
        and row.get('details', {}).get('item_ref') == str(reference['item_id'])
    )
    return {
        **result,
        'status': 'linked' if links else 'definition_only',
        'occurrence_ids': links,
        'profile_locator': f'/profiles/{number}',
        'profile_name': profile.get('name'),
        'item_locator': f'/items/{reference["item_id"]}',
        'item_definition': deepcopy(item),
    }
