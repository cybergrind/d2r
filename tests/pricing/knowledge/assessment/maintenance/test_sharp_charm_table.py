"""Sharp table equivalence requires both native physical modifiers and exact suffix."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_skill_charm_table import ROOT, pin, read


@pytest.fixture(scope='module')
def evidence():
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = build()['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    reviews = []
    for build_id, planner, choices in [
        (
            'double-throw-barbarian-guide',
            'db0106mf',
            [
                ('vita', 201, [338, 339]),
                ('balance', 202, [265]),
                ('inertia', 203, [399]),
                ('plain', 204, []),
                ('maiming', 199, [678]),
            ],
        ),
        ('berserk-barbarian', 'rk0106ln', [('vita', 141, [338, 339]), ('balance', 139, [265]), ('plain', 143, [])]),
        ('dream-paladin', 'zb01066h', [('vita', 126, [338, 339]), ('balance', 127, [265])]),
    ]:
        for suffix, span, suffixes in choices:
            role = next(p for p in profiles if p['id'] == f'{build_id}-main-sharp-{suffix}')
            guide = f'pricing/raw/mr/guides__{build_id}.html'
            occurrence = next(
                o for o in occurrences if o['source_id'] == guide and o['source_locator'] == f'/item-spans/{span}'
            )
            use = next(u for u in uses if u['profile_id'] == role['id'])
            reviews.append(
                {
                    'occurrence_id': occurrence['id'],
                    'occurrence_fingerprint': fingerprint(occurrence),
                    'profile_id': role['id'],
                    'profile_fingerprint': fingerprint(role),
                    'use_fingerprint': fingerprint(use),
                    'review_date': '2026-10-01',
                    'reason': 'Exact native Sharp/suffix table and planner witness.',
                    'pattern_kind': 'native_sharp_grand_charm',
                    'pattern_label': occurrence['original_label'],
                    'guide': pin(guide),
                    'cache': pin('pricing/data/appraisal-guide-sections.json'),
                    'planner': pin(f'pricing/raw/mr/planners/{planner}.json'),
                    'prefixes': pin('third-parties/d2data/json/magicprefix.json'),
                    'prefix_id': 253,
                    'suffixes': pin('third-parties/d2data/json/magicsuffix.json'),
                    'suffix_ids': suffixes,
                }
            )
    return reviews, occurrences, profiles, uses


def test_native_sharp_tables(evidence):
    reviews, occurrences, profiles, uses = evidence
    result = compile_table_equivalence({'schema_version': 1, 'rows': reviews}, occurrences, profiles, uses, ROOT)
    assert len(result) == 10
    assert all(r['state'] == 'reviewed' for r in result)


@pytest.mark.parametrize('mutation', ['prefix', 'suffix', 'unattainable', 'missing-suffix', 'planner'])
def test_sharp_rejects_wrong_source_witness(evidence, mutation):
    reviews, occurrences, profiles, uses = evidence
    review = deepcopy(reviews[0])
    if mutation == 'prefix':
        review['prefix_id'] = 492
    elif mutation == 'suffix':
        review['suffix_ids'] = [399]
    elif mutation == 'unattainable':
        review['suffix_ids'].append(340)
    elif mutation == 'missing-suffix':
        review['suffix_ids'] = []
    else:
        review['planner'] = pin('pricing/raw/mr/planners/vf0106vk.json')
    with pytest.raises(ValueError, match=r'[Ss]harp'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)


@pytest.mark.parametrize('mutation', ['ethereal', 'sockets', 'rare', 'damage', 'ar', 'life', 'totals', 'extra-affix'])
def test_sharp_rejects_inconsistent_planner(evidence, monkeypatch, mutation):
    from pricing.knowledge.assessment.maintenance import sharp_charm_table

    reviews, occurrences, profiles, uses = evidence
    planner = sharp_charm_table.decode_planner(read('pricing/raw/mr/planners/db0106mf.json'))
    item = planner['items']['106']
    if mutation == 'ethereal':
        item['ethereal'] = True
    elif mutation == 'sockets':
        item['sockets'] = 1
    elif mutation == 'rare':
        item['quality'] = 5
    elif mutation == 'damage':
        item['mods']['mp253'][1] = 11
    elif mutation == 'ar':
        item['mods']['mp253'][0] = 77
    elif mutation == 'life':
        item['mods']['ms339'] = [46]
    elif mutation == 'totals':
        item['stats']['maxdamage'] = 9
    else:
        item['mods']['ms399'] = [7]
    monkeypatch.setattr(sharp_charm_table, 'decode_planner', lambda raw: planner)
    with pytest.raises(ValueError, match='Planner'):
        compile_table_equivalence({'schema_version': 1, 'rows': [reviews[0]]}, occurrences, profiles, uses, ROOT)


@pytest.mark.parametrize('mutation', ['prefix-identity', 'suffix-identity', 'minimum'])
def test_maiming_rejects_total_only_role(evidence, mutation):
    reviews, occurrences, profiles, uses = deepcopy(evidence)
    review = next(r for r in reviews if r['suffix_ids'] == [678])
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    predicates = role['must']['all']
    if mutation == 'minimum':
        next(p for p in predicates if p.get('key') == '22:0')['value'] = 7
    else:
        table = mutation.split('-')[0]
        predicates[:] = [p for p in predicates if not (p.get('op') == 'affix_present' and p['table'] == table)]
    use = next(u for u in uses if u['profile_id'] == role['id'])
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='Sharp charm'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)


@pytest.mark.parametrize('mutation', ['plain-total', 'suffix-overflow', 'wrong-sum'])
def test_maiming_rejects_wrong_planner_sum(evidence, monkeypatch, mutation):
    from pricing.knowledge.assessment.maintenance import sharp_charm_table

    reviews, occurrences, profiles, uses = evidence
    review = next(r for r in reviews if r['suffix_ids'] == [678])
    planner = sharp_charm_table.decode_planner(read('pricing/raw/mr/planners/db0106mf.json'))
    item = planner['items']['62']
    if mutation == 'plain-total':
        item['mods'].pop('ms678')
        item['stats']['maxdamage'] = 10
    elif mutation == 'suffix-overflow':
        item['mods']['ms678'] = [5]
    else:
        item['stats']['maxdamage'] = 4
    monkeypatch.setattr(sharp_charm_table, 'decode_planner', lambda raw: planner)
    with pytest.raises(ValueError, match='Planner'):
        compile_table_equivalence({'schema_version': 1, 'rows': [review]}, occurrences, profiles, uses, ROOT)
