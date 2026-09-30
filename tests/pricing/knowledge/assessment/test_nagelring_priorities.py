from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('fire_blast', [True, False])
def test_nagelring_minimum_mf_is_useful_with_source_specific_companions(fire_blast):
    bundle = build()
    rid = 'fire-blast-standard-spirit-nagelring' if fire_blast else 'enchant-mf-nagelring'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    item = replace(
        facts('Ring', 'unique', 'Nagelring'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in [('80:0', 15), ('19:0', 50), ('35:0', 3), ('78:0', 3)]},
    )
    spirit = replace(facts('Monarch'), runeword='Spirit')
    ctx = {
        'player_class': 'Assassin' if fire_blast else 'Sorceress',
        'player_total_fcr': 102,
        'player_equipment': {'off_hand': spirit},
    }

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'80:0'}
    assert evaluate().annotations['80:0']['desirability'] == 'desirable'
    assert not evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != '80:0'})).annotations
    for change in ({'name': 'Other'}, {'rarity': 'magic'}, {'identified': False}, {'ethereal': True}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={**ctx, 'player_class': 'Barbarian'}).annotations
    if fire_blast:
        for shield in (
            None,
            replace(spirit, runeword='Phoenix'),
            replace(spirit, base_code=facts('Crystal Sword').base_code),
            replace(spirit, identified=False),
        ):
            assert not evaluate(context={**ctx, 'player_equipment': {'off_hand': shield}}).annotations
        for value in (None, 101, '102', True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
        assert not evaluate(context={**ctx, 'player_equipment': {}, 'player_items': ['Spirit']}).annotations
        assert not evaluate(
            context={**ctx, 'player_equipment': {}, 'mercenary_equipment': {'off_hand': spirit}}
        ).annotations
    else:
        # Do not inherit a main-loadout threshold or Spirit requirement from a different guide.
        assert set(evaluate(context={'player_class': 'Sorceress'}).annotations) == {'80:0'}
    demand = bundle['guide_demand']['summaries']['Nagelring']
    assert demand['distinct_builds'] == 6
    assert demand['preferred_builds'] == [
        'berserk-barbarian',
        'enchant-sorceress',
        'lightning-strike-amazon',
        'strafe-amazon',
    ]
    assert demand['alternative_builds'] == ['fire-blast-assassin', 'zeal-paladin']
    assert demand['grade'] == 'Pending'


@pytest.mark.parametrize(
    ('rid', 'cls', 'qualification'),
    [
        ('berserk-starter-nagelring', 'Barbarian', 'Angelic'),
        ('berserk-standard-nagelring', 'Barbarian', '105%'),
        ('lightning-strike-starter-nagelring', 'Amazon', '50%'),
    ],
)
def test_attack_build_nagelring_retains_setup_qualifications(rid, cls, qualification):
    bundle = build()
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    assert any(qualification in c for c in role['conditions'])
    config = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(facts('Ring', 'unique', 'Nagelring'), stats={'80:0': {'status': 'decoded', 'value': 15}})

    def evaluate(candidate=item, context=None):
        context = {'player_class': cls} if context is None else context
        return StatsEvaluator().evaluate(
            candidate, config, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert evaluate().annotations['80:0']['desirability'] == 'desirable'
    assert not evaluate(replace(item, stats={})).annotations
    assert not evaluate(context={}).annotations
    assert not evaluate(context={'player_class': 'Sorceress'}).annotations
    for change in ({'rarity': 'rare'}, {'name': 'Other'}, {'ethereal': True}, {'identified': None}):
        assert not evaluate(replace(item, **change)).annotations
    # A main cast-rate total does not prove the separate swap or attack-speed setup.
    assert evaluate(context={'player_class': cls, 'player_total_fcr': 0}).annotations
    outcome = assess_role_results(item, [role], {'player_class': cls})[0]
    assert outcome.status == 'partial'


def test_strafe_nagelring_requires_equipped_stealskull_with_linked_ias_jewel():
    bundle = build()
    rid = 'strafe-mf-stealskull-nagelring'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    config = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    ring = replace(facts('Ring', 'unique', 'Nagelring'), stats={'80:0': {'status': 'decoded', 'value': 15}})
    jewel = {
        'item_type': facts('Jewel', 'magic').item_type,
        'stats_complete': True,
        'stats': {'93:0': {'status': 'decoded', 'value': 15}},
    }
    helmet = replace(facts('Casque', 'unique', 'Stealskull'), sockets=1, socket_contents='filled', socket_items=[jewel])

    def evaluate(head=helmet, **extra):
        context = {'player_class': 'Amazon', 'player_equipment': {'head': head}, **extra}
        return StatsEvaluator().evaluate(
            ring, config, context, role_outcomes=assess_role_results(ring, [role], context)
        )

    assert evaluate().annotations['80:0']['desirability'] == 'desirable'
    for bad in (
        None,
        replace(helmet, name='Harlequin Crest'),
        replace(helmet, identified=None),
        replace(helmet, rarity='rare'),
        replace(helmet, socket_items=[], stats=jewel['stats']),
        facts('Casque', 'unique', 'Stealskull'),
    ):
        assert not evaluate(bad).annotations
    assert not evaluate(None, mercenary_equipment={'head': helmet}).annotations
    assert not evaluate(None, player_items=['Stealskull']).annotations
    assert not evaluate(player_class='Barbarian').annotations
    assert any('breakpoint' in c for c in role['conditions'])
    assert any('planner' in c.lower() for c in role['conditions'])
