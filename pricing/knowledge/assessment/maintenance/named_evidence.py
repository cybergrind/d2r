"""Join named-item review leads without promoting demand to a market tier."""


def index_evidence(definitions, demand, recommendations, item_facts):
    result = {
        key: {
            'recommended_build_occurrences': 0,
            'discovery_occurrences': 0,
            'unresolved_occurrences': 0,
            'build_roles': [],
            'leveling_recommendations': [],
        }
        for key in definitions
    }
    for row in demand:
        key = (row.get('category'), row.get('name'))
        if key not in result:
            continue
        evidence = result[key]
        details = row.get('details', {})
        if details.get('recommended') is False:
            evidence['discovery_occurrences'] += 1
        elif details.get('recommended') is True and details.get('resolution_status') == 'resolved':
            evidence['recommended_build_occurrences'] += 1
            evidence['build_roles'].append(
                {k: row.get(k) for k in ('id', 'build', 'variant', 'side', 'slot', 'source_id', 'source_locator')}
            )
        else:
            evidence['unresolved_occurrences'] += 1
    identities = {row['item_id']: (row.get('quality'), row.get('name')) for row in item_facts}
    for row in recommendations:
        key = identities.get(row.get('item_id'))
        if key not in result or row.get('purpose') != 'leveling' or row.get('name') != key[1]:
            continue
        result[key]['leveling_recommendations'].append(
            {
                k: row.get(k)
                for k in ('id', 'classes', 'archetypes', 'reason', 'conditions', 'source_id', 'source_locator')
            }
        )
    return result
