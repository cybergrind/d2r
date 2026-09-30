from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.assessment.test_fortitude_priorities import MEMBERS as FORTITUDE_MEMBERS


# Same reviewed mercenary loadouts; player armor roles do not imply helmet uses.
MEMBERS = [(s, i, c, m) for s, i, c, side, _base, m in FORTITUDE_MEMBERS if side == 'merc'] + [
    ('double-throw-barbarian-guide', 1, 'Barbarian', 'Act 1 Fire'),
    ('double-throw-barbarian-guide', 2, 'Barbarian', 'Act 1 Fire'),
    ('mirrored-blades-warlock-guide', 1, 'Warlock', 'Act 2 Might'),
    ('mirrored-blades-warlock-guide', 2, 'Warlock', 'Act 2 Might'),
    ('strafe-amazon', 1, 'Amazon', 'Act 2 Might'),
    ('strafe-amazon', 2, 'Amazon', 'Act 2 Might'),
    ('summoner-necromancer-guide', 1, 'Necromancer', 'Act 2 Might'),
    ('summoner-necromancer-guide', 2, 'Necromancer', 'Act 2 Might'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'merc'), MEMBERS)
def test_andariel_native_utility_preserves_fire_penalty_and_socket_qualification(slug, index, cls, merc):
    b = build()
    rid = f'{slug}-{index}-merc-andariel-native'
    role = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'93:0': 20, '60:0': 8, '0:0': 25, '127:0': 2, '39:0': -30, '17:0': 40, '18:0': 40}
    item = replace(
        facts('Demonhead', 'unique', "Andariel's Visage"),
        ethereal=True,
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls, 'mercenary_type': merc}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'93:0', '60:0', '0:0', '127:0'}
    assert evaluate().annotations['93:0']['desirability'] == 'desirable'
    assert evaluate().annotations['60:0']['desirability'] == 'desirable'
    assert evaluate().annotations['0:0']['desirability'] == 'supporting'
    for changes in (
        {'ethereal': False},
        {'ethereal': None},
        {'identified': None},
        {'rarity': 'rare'},
        {'name': 'Other'},
        {'base_code': facts('Bone Visage').base_code},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    for value in (None, 'Act 5 Frenzy', True):
        assert not evaluate(context={**ctx, 'mercenary_type': value}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert any('30%' in c and 'fire' in c for c in role['conditions'])
    assert any('jewel' in c for c in role['conditions'])


def test_andariel_reuses_fissure_configs_and_counts_supported_builds_once():
    b = build()
    d = b['guide_demand']['summaries'].get("Andariel's Visage")
    assert d is not None
    assert d['distinct_builds'] == 17
    assert d['grade'] == 'Pending'
    assert d['lower_bound_grade'] == 'High'
    assert 'fissure-druid' in d['builds']
    assert not any(r['id'].startswith('fissure-druid-') and r['id'].endswith('-andariel-native') for r in b['profiles'])
