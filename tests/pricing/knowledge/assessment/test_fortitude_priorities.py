from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 1, 'Warlock', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('abyss-warlock-build-guide', 2, 'Warlock', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('blessed-hammer-paladin', 1, 'Paladin', 'merc', 'Sacred Armor', 'Act 2 Holy Freeze'),
    ('blessed-hammer-paladin', 3, 'Paladin', 'merc', 'Sacred Armor', 'Act 2 Holy Freeze'),
    ('blizzard-sorceress', 1, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('blizzard-sorceress', 3, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('double-throw-barbarian-guide', 1, 'Barbarian', 'player', 'Archon Plate', None),
    ('fire-blast-assassin', 1, 'Assassin', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('fire-warlock-guide', 1, 'Warlock', 'merc', 'Archon Plate', 'Act 2 Might'),
    ('fire-warlock-guide', 2, 'Warlock', 'merc', 'Archon Plate', 'Act 2 Might'),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('fist-of-the-heavens-paladin', 4, 'Paladin', 'merc', 'Sacred Armor', 'Act 2 Holy Freeze'),
    ('lightning-fury-amazon-guide', 1, 'Amazon', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('lightning-fury-amazon-guide', 2, 'Amazon', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('lightning-sentry-assassin', 1, 'Assassin', 'merc', 'Sacred Armor', 'Act 2 Holy Freeze'),
    ('lightning-sentry-assassin', 2, 'Assassin', 'merc', 'Sacred Armor', 'Act 2 Holy Freeze'),
    ('lightning-sorceress', 1, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('lightning-sorceress', 2, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('meteor-sorceress', 1, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('meteor-sorceress', 3, 'Sorceress', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('poison-nova-necromancer', 1, 'Necromancer', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('poison-nova-necromancer', 2, 'Necromancer', 'merc', 'Sacred Armor', 'Act 2 Might'),
    ('strafe-amazon', 1, 'Amazon', 'player', 'Archon Plate', None),
    ('strafe-amazon', 2, 'Amazon', 'player', 'Archon Plate', None),
    ('wake-of-fire-assassin', 1, 'Assassin', 'merc', 'Sacred Armor', 'Act 2 Might'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'side', 'base', 'merc'), MEMBERS)
def test_fortitude_armor_phys_damage_does_not_become_spell_or_weapon_fit(slug, index, cls, side, base, merc):
    b = build()
    rid = f'{slug}-{index}-{side}-fortitude'
    r = next((r for r in b['profiles'] if r['id'] == rid), None)
    assert r is not None
    configs = [configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'17:0': 300, '18:0': 300, '16:0': 200, '39:0': 25, '41:0': 25, '43:0': 25, '45:0': 25, '105:0': 25}
    item = replace(
        facts(base, name='Fortitude'),
        runeword='Fortitude',
        sockets=4,
        socket_contents='filled',
        ethereal=side == 'merc',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls, **({'mercenary_type': merc} if merc else {})}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [r], context)
        )

    assert set(evaluate().annotations) == set(values) - {'105:0'}
    assert evaluate().annotations['17:0']['desirability'] == 'desirable'
    assert evaluate().annotations['18:0']['desirability'] == 'desirable'
    assert evaluate().annotations['16:0']['desirability'] == 'supporting'
    assert evaluate().annotations['39:0']['desirability'] == 'supporting'
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    weapon = replace(
        facts('Crystal Sword', name='Fortitude'),
        runeword='Fortitude',
        sockets=4,
        socket_contents='filled',
        ethereal=item.ethereal,
        stats=item.stats,
    )
    assert not evaluate(weapon).annotations
    for change in (
        {'runeword': None},
        {'runeword': 'Chains of Honor'},
        {'rarity': 'magic'},
        {'identified': None},
        {'sockets': 3},
        {'socket_contents': 'empty'},
        {'ethereal': side != 'merc'},
        {'base_code': facts('Mage Plate').base_code},
    ):
        assert not evaluate(replace(item, **change)).annotations
    if merc:
        for value in (None, 'Act 5 Frenzy', True):
            assert not evaluate(context={**ctx, 'mercenary_type': value}).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert any('physical' in c for c in r['conditions'])
    assert assess_role_results(item, [r], ctx)[0].status == 'partial'


def test_fortitude_demand_is_deduplicated_and_conflicted_uses_stay_pending():
    b = build()
    d = b['guide_demand']['summaries'].get('Fortitude')
    assert d is not None
    assert d['distinct_builds'] == 16
    assert d['grade'] == 'Pending'
    assert d['lower_bound_grade'] == 'High'
    ids = {r['id'] for r in b['profiles']}
    for rid in [
        'mirrored-blades-warlock-guide-2-merc-fortitude',
        'poison-nova-necromancer-5-merc-fortitude',
        'fire-blast-assassin-2-merc-fortitude',
    ]:
        assert rid not in ids
