"""Explicitly reviewed Fissure armor bearer choices; planner examples are not minima."""

from pricing.knowledge.assessment.maintenance.reviewed_source_issues import reviewed_source_issues
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


CHOICES = ('Act 2 Might', 'Act 2 Holy Freeze')
VARIANTS = {'fissure-merc-standard-fortitude': (1, 'Standard'), 'fissure-merc-magic-find-fortitude': (2, 'Magic Find')}


def required_choice(predicate, values):
    expected = {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': v} for v in values]}
    if predicate == expected:
        return True
    return any(required_choice(child, values) for child in predicate.get('all', ()))


def validate_choices(branch, role, root):
    if 'mercenary_choices' not in branch:
        return
    review = branch.get('choice_review', {})
    index, variant = VARIANTS.get(role['id'], (None, None))
    if (
        index is None
        or branch['mercenary_choices'] != list(CHOICES)
        or role.get('variant') != variant
        or role.get('names') != ['Fortitude']
        or role.get('types') != ['tors']
        or role.get('slot') != 'Body Armor'
        or not review
        or review.get('resolution', {}).get('reviewed_profile_ids') != [role['id']]
        or review.get('resolution', {}).get('mercenary_types') != list(CHOICES)
        or any(review.get('source', {}).get(k) != role['source'].get(k) for k in ('path', 'sha256', 'locator'))
    ):
        raise ValueError('variant mercenary choices lack an exact component review')
    references = [review['source'], *review.get('mechanics', []), *review['resolution'].get('evidence', [])]
    for ref in references:
        path = (root / ref['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('variant mercenary choices evidence escapes the repository')
    if reviewed_source_issues([review], root)[0]['status'] != 'reconciled_source':
        raise ValueError('variant mercenary choices evidence is stale')
    evidence = review['resolution']['evidence']
    planner = 'pricing/raw/mr/planners/tt9vl0l2.json'
    pins = {
        r.get('locator'): r.get('expected')
        for r in evidence
        if r['path'] == planner and r.get('format') == 'maxroll_planner'
    }
    item = pins.get('/items/23', {})
    if (
        pins.get(f'/profiles/{index}/name') != variant
        or pins.get(f'/profiles/{index}/merc') != '10'
        or pins.get(f'/profiles/{index}/mercItems/tors') != 23
        or item.get('unique') != 'runeword067'
        or item.get('sockets') != 4
    ):
        raise ValueError('variant mercenary choices lack the current planner armor and bearer')
    conditions = {
        'all': [role.get('must', {}), *(d['when'] for d in role.get('depends_on', ()) if d.get('required', True))]
    }
    if (
        not requires_eq(conditions, 'context_contains', 'mercenary_items', 'Infinity')
        or not requires_eq(conditions, 'fact_eq', 'runeword', 'Fortitude')
        or not any(requires_eq(p.get('when', {}), 'fact_eq', 'ethereal', True) for p in role.get('preferences', ()))
    ):
        raise ValueError('variant mercenary choices lost the companion or ethereal preference')
