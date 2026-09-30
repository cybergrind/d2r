from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 1, 'Warlock', 'Mage Plate'),
    ('abyss-warlock-build-guide', 2, 'Warlock', 'Mage Plate'),
    ('berserk-barbarian', 1, 'Barbarian', 'Mage Plate'),
    ('berserk-barbarian', 4, 'Barbarian', 'Mage Plate'),
    ('blessed-hammer-paladin', 1, 'Paladin', 'Mage Plate'),
    ('blessed-hammer-paladin', 2, 'Paladin', 'Mage Plate'),
    ('double-throw-barbarian-guide', 2, 'Barbarian', 'Archon Plate'),
    ('dragon-talon-assassin', 1, 'Assassin', 'Mage Plate'),
    ('dream-paladin', 0, 'Paladin', 'Mage Plate'),
    ('echoing-strike-warlock-guide', 1, 'Warlock', 'Mage Plate'),
    ('echoing-strike-warlock-guide', 2, 'Warlock', 'Mage Plate'),
    ('echoing-strike-warlock-guide', 3, 'Warlock', 'Mage Plate'),
    ('fire-blast-assassin', 1, 'Assassin', 'Mage Plate'),
    ('fire-warlock-guide', 1, 'Warlock', 'Mage Plate'),
    ('fire-warlock-guide', 2, 'Warlock', 'Mage Plate'),
    ('fissure-druid', 1, 'Druid', 'Archon Plate'),
    ('fissure-druid', 2, 'Druid', 'Archon Plate'),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', 'Mage Plate'),
    ('fist-of-the-heavens-paladin', 3, 'Paladin', 'Mage Plate'),
    ('gold-find-barbarian', 1, 'Barbarian', 'Mage Plate'),
    ('gold-find-barbarian', 2, 'Barbarian', 'Mage Plate'),
    ('gold-find-barbarian', 3, 'Barbarian', 'Mage Plate'),
    ('lightning-fury-amazon-guide', 1, 'Amazon', 'Dusk Shroud'),
    ('lightning-fury-amazon-guide', 2, 'Amazon', 'Dusk Shroud'),
    ('lightning-sentry-assassin', 1, 'Assassin', 'Mage Plate'),
    ('lightning-sentry-assassin', 2, 'Assassin', 'Mage Plate'),
    ('lightning-sorceress', 1, 'Sorceress', 'Mage Plate'),
    ('lightning-strike-amazon', 1, 'Amazon', 'Mage Plate'),
    ('mirrored-blades-warlock-guide', 1, 'Warlock', 'Mage Plate'),
    ('mirrored-blades-warlock-guide', 2, 'Warlock', 'Mage Plate'),
    ('poison-nova-necromancer', 1, 'Necromancer', 'Mage Plate'),
    ('poison-nova-necromancer', 2, 'Necromancer', 'Mage Plate'),
    ('summoner-necromancer-guide', 1, 'Necromancer', 'Archon Plate'),
    ('summoner-necromancer-guide', 2, 'Necromancer', 'Archon Plate'),
    ('wake-of-fire-assassin', 1, 'Assassin', 'Mage Plate'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'base'), MEMBERS)
def test_enigma_armor_preserves_source_base_and_actual_mobility_stats(slug, index, cls, base):
    bundle = build()
    rid = f'{slug}-{index}-player-enigma'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'127:0': 2, '97:54': 1, '96:0': 45, '36:0': 8, '76:0': 5, '220:0': 6, '240:0': 8, '31:0': 1000}
    item = replace(
        facts(base, name='Enigma'),
        runeword='Enigma',
        sockets=3,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    context = {'player_class': cls}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate().annotations) == set(values)
    assert evaluate().annotations['97:54']['desirability'] == ('supporting' if cls == 'Sorceress' else 'desirable')
    assert evaluate().annotations['31:0']['desirability'] == 'supporting'
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    for change in [
        {'runeword': None},
        {'rarity': 'magic'},
        {'sockets': 2},
        {'socket_contents': 'empty'},
        {'ethereal': True},
        {'identified': None},
        {'base_code': facts('Quilted Armor').base_code},
    ]:
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(ctx={'player_class': 'Other'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert any('cast rate' in c for c in role['conditions'])


def test_enigma_demand_deduplicates_variants_and_excludes_unendorsed_planners():
    bundle = build()
    assert bundle['guide_demand']['summaries']['Enigma']['distinct_builds'] >= 20
    assert bundle['guide_demand']['summaries']['Enigma']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['Enigma']['builds'])
    )

    ids = {r['id'] for r in bundle['profiles']}
    for rid in [
        'berserk-barbarian-5-player-enigma',
        'fire-blast-assassin-2-player-enigma',
        'wake-of-fire-assassin-3-player-enigma',
    ]:
        assert rid not in ids
