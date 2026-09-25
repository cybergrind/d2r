"""Deduplicate source blockers while retaining every affected guide reference."""

import json
from copy import deepcopy


def source_conflicts(links, planners):
    groups = {}
    for link in links:
        status = link['status']
        if status not in {'missing_planner', 'missing_set', 'ambiguous_set', 'missing_item'}:
            continue
        reference = link['reference']
        source = link['planner_source_id']
        set_id = reference.get('set_id') if status != 'missing_planner' else None
        item_id = reference.get('item_id') if status == 'missing_item' else None
        key = json.dumps([source, status, set_id, item_id])
        group = groups.setdefault(
            key,
            {
                'planner_source_id': source,
                'reason': status,
                'requested_set_id': set_id,
                'requested_item_id': item_id,
                'disposition': 'blocked_source',
                'available_sets': [
                    {'uid': p.get('uid'), 'name': p.get('name')}
                    for p in (planners.get(source) or {}).get('profiles', [])
                ],
                'affected_references': [],
            },
        )
        group['affected_references'].append(deepcopy(link))
    for group in groups.values():
        group['affected_references'].sort(key=lambda r: json.dumps(r, sort_keys=True))
    return [groups[key] for key in sorted(groups)]
