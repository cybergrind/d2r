from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_raven_claw_prioritizes_enchant_delivery_not_physical_weapon_damage():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'] == 'enchant-raven-claw-alternative']
    assert len(roles) == 1
    item = replace(
        facts('Long Bow', 'unique', 'Raven Claw'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {'158:0': 3, '17:0': 60, '18:0': 60}.items()},
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    context = {'player_class': 'Sorceress'}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, roles, context)
        )

    assert set(evaluate(item).annotations) == {'158:0'}
    assert not evaluate(replace(item, ethereal=True)).annotations
    assert not evaluate(replace(item, base_code=facts('Short Bow').base_code)).annotations
    assert not evaluate(replace(item, rarity='magic')).annotations


def test_scalper_alternatives_require_elite_upgrade_and_sustainable_ethereal_stack():
    roles = [r for r in build()['profiles'] if r['id'].startswith('double-throw-scalper-')]
    assert len(roles) == 4
    for role in roles:
        ethereal = '-ethereal-' in role['id']
        item = replace(
            facts('Flying Axe', 'unique', 'The Scalper'),
            ethereal=ethereal,
            stats={
                '253:0': {'status': 'decoded', 'value': 30},
                '17:0': {'status': 'decoded', 'value': 150},
                '18:0': {'status': 'decoded', 'value': 150},
            },
        )

        def assess(candidate, cls='Barbarian', role=role):
            return assess_roles(candidate, [role], {'player_class': cls})[0]

        assert assess(item)['status'] == 'matched'
        assert assess(replace(item, base_code=facts('Francisca').base_code))['status'] == 'failed'
        assert assess(replace(item, ethereal=not ethereal))['status'] == 'failed'
        assert assess(replace(item, sockets=1, socket_contents='filled'))['status'] == 'failed'
        assert assess(item, 'Sorceress')['status'] == 'failed'
        if ethereal:
            assert assess(replace(item, stats={'253:0': {'status': 'decoded', 'value': 0}}))['status'] == 'failed'
            assert assess(replace(item, stats={}))['status'] != 'matched'
