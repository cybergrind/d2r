from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 0, 'Warlock', 'Act 2 Might', 'Mage Plate', True),
    ('berserk-barbarian', 1, 'Barbarian', 'Act 2 Might', 'Archon Plate', True),
    ('dream-paladin', 0, 'Paladin', 'Act 2 Might', 'Archon Plate', True),
    ('echoing-strike-warlock-guide', 0, 'Warlock', 'Act 2 Blessed Aim', 'Mage Plate', True),
    ('enchant-sorceress', 0, 'Sorceress', 'Act 1 Fire', 'Mage Plate', True),
    ('fire-warlock-guide', 0, 'Warlock', 'Act 2 Might', 'Mage Plate', True),
    ('gold-find-barbarian', 0, 'Barbarian', 'Act 2 Might', 'Mage Plate', False),
    ('lightning-fury-amazon-guide', 3, 'Amazon', 'Act 5 Frenzy', 'Mage Plate', True),
    ('lightning-sorceress', 3, 'Sorceress', 'Act 5 Frenzy', 'Archon Plate', False),
    ('lightning-strike-amazon', 2, 'Amazon', 'Act 5 Frenzy', 'Archon Plate', True),
    ('meteor-sorceress', 4, 'Sorceress', 'Act 2 Might', 'Archon Plate', False),
    ('nova-sorceress-guide', 0, 'Sorceress', 'Act 2 Holy Freeze', 'Light Plate', True),
    ('strafe-amazon', 0, 'Amazon', 'Act 2 Might', 'Mage Plate', True),
    ('summoner-necromancer-guide', 0, 'Necromancer', 'Act 2 Might', 'Breast Plate', True),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'merc', 'base', 'requires_ethereal'), MEMBERS)
def test_treachery_component_keeps_recipe_context_and_fade_activation(slug, index, cls, merc, base, requires_ethereal):
    bundle = build()
    rid = f'{slug}-{index}-merc-treachery-native'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts(base, 'normal', 'Treachery'),
        runeword='Treachery',
        ethereal=True,
        sockets=3,
        socket_contents='filled',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('93:0', 45), ('201:17103', 5), ('99:0', 20), ('43:0', 30), ('83:6', 2), ('60:0', 8)]
        },
    )
    context = {'player_class': cls, 'mercenary_type': merc, 'activity': 'Uber Mephisto'}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    keys = {'201:17103', '99:0', '43:0'}
    if merc != 'Act 5 Frenzy':
        keys.add('93:0')
    assert set(evaluate().annotations) == keys
    assert evaluate().annotations['201:17103']['desirability'] == 'desirable'
    assert bool(evaluate(replace(item, ethereal=False)).annotations) is not requires_ethereal
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    for changes in (
        {'runeword': 'Fortitude'},
        {'sockets': 2},
        {'socket_contents': 'empty'},
        {'socket_contents': 'unknown'},
        {'identified': None},
        {'ethereal': None},
        {'base_code': facts('Sacred Armor').base_code},
        {'rarity': 'magic'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={**context, 'mercenary_type': None}).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Other'}).annotations
    if slug == 'lightning-sorceress':
        assert not evaluate(ctx={**context, 'activity': 'Cows'}).annotations
    assert assess_role_results(item, [role], context)[0].status == 'partial'
    assert any('active' in c and 'Fade' in c for c in role['conditions'])
    assert not evaluate(replace(item, stats={})).annotations


def test_treachery_family_reuses_existing_branches_without_promoting_armor_conflict():
    bundle = build()
    demand = bundle['guide_demand']['summaries']['Treachery']
    assert demand['distinct_builds'] == 17
    # Echoing's Starter armor and two Ubers prebuff uses count as one build.
    assert len([c for c in demand['contexts'] if c['build'] == 'echoing-strike-warlock-guide']) == 3
    assert demand['grade'] == 'Pending'
    assert demand['lower_bound_grade'] == 'High'
    assert any(r['id'] == 'smite-shared-treachery' for r in bundle['profiles'])
    assert any(r['id'] == 'fissure-starter-merc-treachery' for r in bundle['profiles'])
    assert not any(
        r['id'].startswith('double-throw-') and r['id'].endswith('-treachery-native') for r in bundle['profiles']
    )
