"""Pure demand counts shared by offline compilation and prepared-result selection."""


def breadth_grade(count):
    return 'High' if count >= 5 else 'Med' if count >= 2 else 'Low' if count else 'No reviewed use'


def summarize_demand(uses, *, complete):
    accepted = [
        r
        for r in uses
        if r.get('review_state') == 'reviewed'
        and r.get('scope') == 'softcore'
        and not r.get('historical')
        and r.get('build')
        and r['build'] != 'shared-planner'
        and r.get('strength') in {'required', 'preferred', 'alternative'}
    ]
    builds = sorted({r['build'] for r in accepted})
    contexts = sorted({(r['build'], r['variant'], r['side'], r['strength']) for r in accepted})
    grade = breadth_grade(len(builds))
    return {
        'rubric_version': 1,
        'complete': complete,
        'grade': grade if complete else 'Pending',
        'lower_bound_grade': grade,
        'distinct_builds': len(builds),
        'builds': builds,
        'preferred_builds': sorted({r['build'] for r in accepted if r['strength'] in {'required', 'preferred'}}),
        'alternative_builds': sorted({r['build'] for r in accepted if r['strength'] == 'alternative'}),
        'contexts': [dict(zip(('build', 'variant', 'side', 'strength'), c, strict=True)) for c in contexts],
    }
