"""Prioritize unreviewed named identities using demand and cached evidence gaps."""


def next_action(row):
    if row['status'] == 'invalid_source':
        return 'repair_source_evidence'
    market = row['market']
    if market is None:
        return 'audit_cached_market'
    if market['structurally_ready']:
        return 'review_exact_comparisons'
    if market['scoped_observations']:
        return 'resolve_listing_facets'
    return 'find_scoped_evidence'


def review_queue(rows):
    queue = []
    for row in rows:
        if row['status'] == 'reviewed_policy':
            continue
        evidence = row['evidence']
        queue.append(
            {
                'quality': row['quality'],
                'name': row['name'],
                'next_action': next_action(row),
                'recommended_build_occurrences': evidence['recommended_build_occurrences'],
                'leveling_recommendations': len(evidence['leveling_recommendations']),
                'market': row['market'],
            }
        )
    return sorted(
        queue,
        key=lambda row: (
            -row['recommended_build_occurrences'],
            -row['leveling_recommendations'],
            -(row['market'] or {}).get('structurally_ready', 0),
            row['quality'],
            row['name'],
        ),
    )
