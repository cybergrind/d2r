"""A source discrepancy cannot silently widen a variant's mercenary bearer."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.variant_prose_context import matches


CHOICES = ('Act 2 Might', 'Act 2 Holy Freeze')


def inputs():
    role = {
        'side': 'merc',
        'must': {'op': 'context_eq', 'field': 'player_class', 'value': 'Druid'},
        'depends_on': [
            {'when': {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': c} for c in CHOICES]}}
        ],
    }
    branch = {'player_class': 'Druid', 'mercenary_type': CHOICES[0], 'mercenary_choices': list(CHOICES)}
    return branch, role, {'class': 'Druid'}, 'Act 2 Might Mercenary with Infinity'


def test_explicit_source_choices_match_only_the_required_disjunction():
    assert matches(*inputs())


@pytest.mark.parametrize('change', ['optional', 'extra-bearer', 'missing-choice', 'missing-prose-bearer'])
def test_choice_match_rejects_unproved_bearers(change):
    branch, role, occurrence, quote = deepcopy(inputs())
    if change == 'optional':
        role['depends_on'][0]['required'] = False
    elif change == 'extra-bearer':
        role['depends_on'][0]['when']['any'].append(
            {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 5 Frenzy'}
        )
    elif change == 'missing-choice':
        branch['mercenary_choices'] = [CHOICES[0]]
    else:
        branch['mercenary_choices'] = [CHOICES[1]]
    assert not matches(branch, role, occurrence, quote)


def evidence():
    import hashlib
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
    from pricing.knowledge.assessment.maintenance.source_context_reviews import OCCURRENCE_FIELDS
    from pricing.knowledge.assessment.policies.sources import resolve_pointer

    guide = 'pricing/raw/mr/guides__fissure-druid.html'
    cache_path = 'pricing/data/appraisal-guide-sections.json'
    cache = json.loads(Path(cache_path).read_text())['sources'][guide]
    pin = {'path': cache_path, 'sha256': hashlib.sha256(Path(cache_path).read_bytes()).hexdigest()}
    prefix = '/sources/' + guide.replace('/', '~1')
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())['occurrences']
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    issues = json.loads(Path('pricing/knowledge/assessment/rules/reviewed_source_issues.json').read_text())['reviews']
    original = next(r for r in issues if r['id'] == 'fissure-standard-mf-mercenary-aura')
    rows = []
    for span, section, slug in ((23, 17, 'standard'), (26, 21, 'magic-find')):
        rid = f'fissure-merc-{slug}-fortitude'
        role = next(p for p in profiles if p['id'] == rid)
        o = next(o for o in inventory if o['source_id'] == guide and o['source_locator'] == f'/item-spans/{span}')
        choice = deepcopy(original)
        choice['id'] = rid + '-component-aura-review'
        choice['review_date'] = choice['resolution']['review_date'] = '2026-09-28'
        source = role['source']
        primary = resolve_pointer(json.loads(Path(source['path']).read_text()), source['locator'])
        choice['source'] = {k: source[k] for k in ('path', 'sha256', 'locator')}
        choice['source']['expected'] = primary
        choice['resolution']['reviewed_profile_ids'] = [rid]
        choice['resolution']['mercenary_types'] = list(CHOICES)
        choice['review'] = choice['resolution']['review'] = (
            'Exact variant prose establishes Fortitude armor utility without a required base or ethereal status. '
            'Current planner corroborates Holy Freeze as an alternative to prose Might. Its ethereal Sacred Armor '
            'is an example, not a minimum or universal best base. Independently reviewed broader armor component: '
            'legal completed armor recipe, Druid, either reviewed Act 2 bearer and Infinity remain required; '
            'ethereal remains preferred. No perfect rolls or complete loadout equivalence inferred.'
        )
        rows.append(
            {
                'id': rid + '-prose',
                'kind': 'variant_mercenary_narrative',
                'review_date': '2026-09-28',
                'occurrence_id': o['id'],
                'expected_occurrence': {k: o.get(k) for k in (*OCCURRENCE_FIELDS, 'class')},
                'reason': choice['review'],
                'source': {**pin, 'locator': prefix + f'/item_spans/{span}', 'expected': cache['item_spans'][span]},
                'evidence': {
                    **pin,
                    'locator': prefix + f'/sections/{section}/text',
                    'quote': cache['sections'][section]['text'],
                },
                'branches': [
                    {
                        'profile_id': rid,
                        'profile_fingerprint': fingerprint(role),
                        'variant': role['variant'],
                        'slot': role['slot'],
                        'player_class': 'Druid',
                        'mercenary_type': CHOICES[0],
                        'mercenary_choices': list(CHOICES),
                        'choice_review': choice,
                    }
                ],
                'remaining_branches': [],
            }
        )
    return {'schema_version': 1, 'rows': rows}, inventory, profiles, uses


def test_fissure_variant_choices_validate_prose_current_planner_and_component_scope():
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews

    result = compile_source_context_reviews(*evidence(), Path.cwd())
    assert len(result) == 2
    assert all(r['state'] == 'reviewed' for r in result)


@pytest.mark.parametrize(
    'change', ['missing-review', 'narrower-profile', 'wrong-aura', 'missing-item', 'wrong-variant']
)
def test_variant_choice_proof_cannot_reuse_a_different_component_or_planner(change):
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews

    doc, occurrences, profiles, uses = evidence()
    doc['rows'] = doc['rows'][:1]
    branch = doc['rows'][0]['branches'][0]
    resolution = branch['choice_review']['resolution']
    if change == 'missing-review':
        del branch['choice_review']
    elif change == 'narrower-profile':
        resolution['reviewed_profile_ids'] = ['fissure-druid-1-merc-fortitude']
    elif change == 'wrong-aura':
        next(r for r in resolution['evidence'] if r.get('locator') == '/profiles/1/merc')['expected'] = '11'
    elif change == 'wrong-variant':
        resolution['evidence'] = [
            r for r in resolution['evidence'] if not r.get('locator', '').startswith('/profiles/1/')
        ]
    else:
        resolution['evidence'] = [r for r in resolution['evidence'] if r.get('locator') != '/items/23']
    with pytest.raises(ValueError, match='variant mercenary choices'):
        compile_source_context_reviews(doc, occurrences, profiles, uses, Path.cwd())


def test_repository_retains_both_fissure_component_reviews():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.source_context_reviews import compile_source_context_reviews

    expected, occurrences, profiles, uses = evidence()
    document = json.loads(Path('pricing/knowledge/assessment/rules/source_context_reviews.json').read_text())
    result = compile_source_context_reviews(document, occurrences, profiles, uses, Path.cwd())
    linked = {r['occurrence_id']: r for r in result}
    for row in expected['rows']:
        actual = linked[row['occurrence_id']]
        assert actual['state'] == 'reviewed'
        assert actual['profile_ids'] == [row['branches'][0]['profile_id']]
