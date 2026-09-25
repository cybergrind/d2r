"""Lossless display grouping; assessment evidence and role records stay unchanged."""


def display_groups(roles):
    groups = {}
    for role in roles:
        details = {
            'missing': list(dict.fromkeys(role['missing'])),
            'improvements': list(
                dict.fromkeys(p['label'] for p in role.get('preferences', []) if p['status'] == 'false')
            ),
            'alternatives': list(dict.fromkeys(role['alternatives'])),
        }
        key = (
            *(role.get(k) for k in ('build', 'side', 'slot', 'role', 'status')),
            *(tuple(sorted(values)) for values in details.values()),
        )
        group = groups.setdefault(key, {'role': role, 'variants': [], **details})
        if role['variant'] not in group['variants']:
            group['variants'].append(role['variant'])
    return list(groups.values())


def shared_details(groups):
    if len(groups) < 2:
        return {'missing': [], 'improvements': []}
    return {
        key: [value for value in groups[0][key] if all(value in group[key] for group in groups[1:])]
        for key in ('missing', 'improvements')
    }
