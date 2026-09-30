from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('dream-paladin', 1, 'Paladin', 'Act 1 Cold', True),
    ('dream-paladin', 2, 'Paladin', 'Act 1 Cold', False),
    ('lightning-strike-amazon', 1, 'Amazon', 'Act 1 Cold', False),
    ('strafe-amazon', 1, 'Amazon', 'Act 2 Might', True),
    ('strafe-amazon', 2, 'Amazon', 'Act 2 Might', True),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'merc', 'original_only'), MEMBERS)
def test_shaftstop_defenses_do_not_inherit_helmet_leech_or_jewel_speed(slug, index, cls, merc, original_only):
    b = build()
    rid = f'{slug}-{index}-merc-shaftstop'
    role = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Mesh Armor', 'unique', 'Shaftstop'),
        ethereal=True,
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('36:0', 30), ('7:0', 60), ('16:0', 180), ('60:0', 8), ('93:0', 15)]
        },
    )
    ctx = {'player_class': cls, 'mercenary_type': merc}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'36:0', '7:0'}
    assert evaluate().annotations['36:0']['desirability'] == 'desirable'
    assert evaluate().annotations['7:0']['desirability'] == 'supporting'
    assert bool(evaluate(replace(item, ethereal=False)).annotations) == (slug == 'strafe-amazon')
    assert bool(evaluate(replace(item, base_code=facts('Boneweave').base_code)).annotations) is not original_only
    for changes in (
        {'ethereal': None},
        {'identified': None},
        {'name': 'Other'},
        {'rarity': 'set'},
        {'base_code': facts('Chain Mail').base_code},
        {'base_code': facts('Shadow Plate').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for mercenary in (None, 'Act 5 Frenzy', True):
        assert not evaluate(context={**ctx, 'mercenary_type': mercenary}).annotations
    assert not evaluate(context={**ctx, 'player_class': 'Other'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert any('life leech' in c for c in role['conditions'])
    if slug == 'strafe-amazon':
        assert any('alternative' in c for c in role['conditions'])


def test_shaftstop_distinct_build_demand_preserves_alternative_and_conflict():
    b = build()
    d = b['guide_demand']['summaries'].get('Shaftstop')
    assert d is not None
    assert d['distinct_builds'] == 5
    assert d['lower_bound_grade'] == 'High'
    assert d['grade'] == 'Pending'
    assert d['alternative_builds'] == ['abyss-warlock-build-guide', 'strafe-amazon', 'zeal-paladin']
    assert not any(
        r['id'].startswith('double-throw-barbarian-guide-') and r['id'].endswith('-shaftstop') for r in b['profiles']
    )
