"""Planner structure reconciliation without re-extracting item names or demand."""

from collections import defaultdict

from pricing.knowledge.builds import decode_planner


def audit_planner_slots(document, source, occurrences):
    planner = decode_planner(document)
    rows = [r for r in occurrences if r['source_id'] == source]
    index = defaultdict(list)
    for row in rows:
        index[row['source_locator']].append(row)
    slots, containers, profiles, accounted, used = [], [], [], set(), set()

    def visit(ref, locator, ancestors=()):
        key = str(ref)
        matches = [r['id'] for r in index[locator] if r.get('details', {}).get('item_ref') == key]
        status = 'represented' if matches else 'conflict' if index[locator] else 'missing_occurrence'
        if ref is None:
            status = 'empty' if not index[locator] else 'conflict'
        if key in ancestors:
            status = 'cyclic_reference'
        slots.append({'locator': locator, 'reference': ref, 'status': status, 'occurrence_ids': matches})
        accounted.update(matches)
        if ref is None or key in ancestors:
            return
        item = ref if isinstance(ref, dict) else planner['items'].get(key)
        if item is None:
            # Literal base/rune references are legal; resolution belongs to the ledger.
            return
        used.add(key)
        children = item.get('socketedItems', [])
        if not isinstance(children, list):
            containers.append({'locator': locator + '/socketedItems', 'status': 'unsupported_shape'})
            return
        for ordinal, child in enumerate(children):
            visit(child, f'{locator}/socketedItems/{ordinal}', (*ancestors, key))

    for number, profile in enumerate(planner['profiles']):
        profiles.append(
            {
                'locator': f'/profiles/{number}',
                'name': profile.get('name'),
                'uid': profile.get('uid'),
                'mercenary_id': profile.get('merc'),
            }
        )
        for container in ('items', 'mercItems', 'inventory', 'cube'):
            locator = f'/profiles/{number}/{container}'
            value = profile.get(container)
            status = (
                'absent'
                if container not in profile
                else 'unsupported_shape'
                if not isinstance(value, (dict, list))
                else 'present'
                if value
                else 'empty'
            )
            containers.append({'locator': locator, 'status': status})
            if status not in {'present', 'empty'}:
                continue
            for slot, ref in value.items() if isinstance(value, dict) else enumerate(value):
                visit(ref, f'{locator}/{slot}')
    for key in sorted(set(planner['items']) - used):
        visit(key, f'/items/{key}')
    return {
        'source_id': source,
        'complete': False,
        'profiles': profiles,
        'containers': containers,
        'slots': slots,
        'unaccounted_occurrence_ids': sorted(r['id'] for r in rows if r['id'] not in accounted),
        'scope': 'Structural reference coverage only; guide endorsement and aliases require review.',
    }
