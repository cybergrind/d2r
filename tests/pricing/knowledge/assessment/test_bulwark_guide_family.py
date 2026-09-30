from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 'Warlock', 'Act 2 Might', 'Bone Visage', True),
    ('berserk-barbarian', 'Barbarian', 'Act 2 Might', 'Death Mask', False),
    ('blessed-hammer-paladin', 'Paladin', 'Act 2 Holy Freeze', 'Crown', True),
    ('blizzard-sorceress', 'Sorceress', 'Act 2 Might', 'Diadem', False),
    ('double-throw-barbarian-guide', 'Barbarian', 'Act 2 Might', 'Crown', True),
    ('echoing-strike-warlock-guide', 'Warlock', 'Act 2 Blessed Aim', 'Crown', True),
    ('enchant-sorceress', 'Sorceress', 'Act 1 Fire', 'Diadem', True),
    ('fire-warlock-guide', 'Warlock', 'Act 2 Might', 'Crown', True),
    ('lightning-fury-amazon-guide', 'Amazon', 'Act 2 Might', 'Death Mask', False),
    ('lightning-sentry-assassin', 'Assassin', 'Act 2 Holy Freeze', 'Tiara', False),
    ('lightning-sorceress', 'Sorceress', 'Act 2 Holy Freeze', 'Death Mask', False),
    ('lightning-strike-amazon', 'Amazon', 'Act 2 Holy Freeze', 'Death Mask', False),
    ('nova-sorceress-guide', 'Sorceress', 'Act 2 Holy Freeze', 'Crown', False),
    ('poison-nova-necromancer', 'Necromancer', 'Act 2 Might', 'Death Mask', False),
    ('smite-paladin', 'Paladin', 'Act 2 Holy Freeze', 'Crown', False),
    ('strafe-amazon', 'Amazon', 'Act 2 Might', 'Crown', False),
    ('wake-of-fire-assassin', 'Assassin', 'Act 2 Might', 'Tiara', False),
]


@pytest.mark.parametrize(('slug', 'cls', 'merc', 'base', 'requires_ethereal'), MEMBERS)
def test_bulwark_starter_native_rolls_are_useful_without_perfect_defense(slug, cls, merc, base, requires_ethereal):
    bundle = build()
    rid = f'{slug}-0-merc-bulwark-native'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts(base, 'normal', 'Bulwark'),
        runeword='Bulwark',
        ethereal=True,
        sockets=3,
        socket_contents='filled',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('60:0', 4), ('36:0', 10), ('76:0', 5), ('99:0', 20), ('16:0', 75), ('93:0', 15)]
        },
    )
    context = {'player_class': cls, 'mercenary_type': merc}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate().annotations) == {'60:0', '36:0', '76:0', '99:0'}
    assert evaluate().annotations['60:0']['desirability'] == 'desirable'
    assert evaluate().annotations['36:0']['desirability'] == 'desirable'
    assert bool(evaluate(replace(item, ethereal=False)).annotations) is not requires_ethereal
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    for changes in (
        {'runeword': 'Cure'},
        {'sockets': 2},
        {'socket_contents': 'empty'},
        {'identified': None},
        {'ethereal': None},
        {'base_code': facts('Diadem' if base != 'Diadem' else 'Crown').base_code},
        {'rarity': 'magic'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={**context, 'mercenary_type': None}).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Other'}).annotations
    assert assess_role_results(item, [role], context)[0].status == 'partial'
    assert any('physical damage' in c for c in role['conditions'])
    assert not evaluate(replace(item, stats={})).annotations


def test_bulwark_preserves_unresolved_alternatives_and_counts_distinct_builds():
    bundle = build()
    demand = bundle['guide_demand']['summaries']['Bulwark']
    expected_builds = {row[0] for row in MEMBERS} | {'fissure-druid', 'fist-of-the-heavens-paladin', 'zeal-paladin'}
    assert set(demand['builds']) == expected_builds
    assert demand['distinct_builds'] == len(expected_builds)
    assert demand['grade'] == 'Pending'
    assert demand['lower_bound_grade'] == 'High'
    assert not any(
        r['id'].startswith(('summoner-necromancer-guide-',)) and r['id'].endswith('-bulwark-native')
        for r in bundle['profiles']
    )
