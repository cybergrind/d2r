from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_hustle_weapon_uses_preserve_equipment_and_proc_context():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-hustle-weapon-alternative')]
    assert len(roles) == 13
    for role in roles:
        merc = role['side'] == 'merc'
        base = 'Partizan' if merc else ('Grand Matron Bow' if role['build'] == 'strafe-amazon' else 'Phase Blade')
        context = {'player_class': role['must']['all'][0]['value']}
        if merc:
            context['mercenary_type'] = (
                'Act 2 Holy Freeze' if role['build'] == 'lightning-strike-amazon' else 'Act 2 Might'
            )
        values = {'17:0': 180, '18:0': 180, '93:0': 30, '151:122': 1, '198:16513': 5}
        item = replace(
            facts(base, 'normal', 'Hustle (weapon)'),
            runeword='Hustle (weapon)',
            sockets=3,
            socket_contents='filled',
            ethereal=merc,
            stats={
                k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
                for k, v in values.items()
            },
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, ctx=context, role=role, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        expected = set(values) if merc else {'93:0', '198:16513'}
        if role['build'] == 'zeal-paladin':
            expected |= {'17:0', '18:0'}
        assert set(evaluate(item).annotations) == expected
        for quality in ('superior', 'low_quality'):
            assert set(evaluate(replace(item, rarity=quality)).annotations) == expected
        for changes in (
            {'runeword': 'Hustle (armor)'},
            {'sockets': 2},
            {'socket_contents': 'empty'},
            {'rarity': 'magic'},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        if merc:
            assert not evaluate(item, {**context, 'mercenary_type': 'Act 1 Fire'}).annotations
            assert not evaluate(replace(item, base_code=facts('Phase Blade').base_code)).annotations
        elif role['build'] == 'strafe-amazon':
            assert not evaluate(replace(item, ethereal=True)).annotations
        assert 'proc' in ' '.join(role['conditions']).lower()
