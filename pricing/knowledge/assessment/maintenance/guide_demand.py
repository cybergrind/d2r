"""Guide breadth over explicit reviewed endorsements, independent of price or fit."""

from pricing.knowledge.assessment.demand_counts import summarize_demand


def review_key(row):
    if 'pattern' in row:
        if 'item' in row or not row['pattern'] or row['pattern'] != row['profile_id']:
            raise ValueError('Pattern demand must reference its exact reviewed configuration')
        return 'pattern:' + row['pattern']
    return row['item']


def compile_demand(uses, profiles):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    by_id = {p['id']: p for p in profiles}
    for row in uses:
        profile = by_id.get(row['profile_id'])
        if (
            not profile
            or ('pattern' not in row and row['item'] not in profile.get('names', []))
            or ('pattern' in row and bool(profile.get('names')))
            or any(row.get(k) != profile.get(k) for k in ('build', 'variant', 'side', 'source'))
            or row.get('profile_fingerprint') != fingerprint(profile)
        ):
            raise ValueError(f'Stale guide-use review: {row["profile_id"]}')
    summaries = {}
    for item in sorted({review_key(r) for r in uses}):
        rows = [r for r in uses if review_key(r) == item]
        summary = summarize_demand(rows, complete=False)
        if 'pattern' in rows[0]:
            summary['scope'] = 'pattern'
            summary['profile_ids'] = sorted({r['profile_id'] for r in rows})
        presentation = {}
        for row in rows:
            if 'presentation' not in row:
                continue
            spec = row['presentation']
            if set(spec) != {'progression'} or spec['progression'] not in {'Starter', 'Budget', 'Endgame', 'Ubers'}:
                raise ValueError('Unsupported reviewed progression')
            presentation[row['profile_id']] = dict(spec)
        if presentation:
            summary['role_presentation'] = presentation
        summaries[item] = summary
    return summaries


def main():
    import hashlib
    import json

    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.refresh import atomic_json

    path = ROOT / 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
    raw = path.read_bytes()
    reviews = json.loads(raw)
    if reviews.get('schema_version') != 1:
        raise ValueError('Unsupported guide review schema')
    summaries = compile_demand(reviews['uses'], build()['profiles'])
    atomic_json(
        ROOT / 'pricing/data/appraisal-guide-demand-reviewed.json',
        {
            'schema_version': 1,
            'complete': False,
            'review_sha256': hashlib.sha256(raw).hexdigest(),
            'review_path': str(path.relative_to(ROOT)),
            'summaries': summaries,
            'uses': reviews['uses'],
        },
    )
    print(json.dumps(summaries))


if __name__ == '__main__':
    main()
