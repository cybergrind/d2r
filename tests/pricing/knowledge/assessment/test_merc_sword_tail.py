from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_lawbringer_uses_respect_sword_handedness_bearer_and_proc_units():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == ['Lawbringer'] and r['id'].endswith('-merc-sword-tail')]
    assert len(roles) == 7
    values = {
        '151:119': 18,
        '198:5583': 20,
        '60:0': 7,
        '32:0': 250,
        '2:0': 10,
        '116:0': 50,
        '48:0': 150,
        '49:0': 210,
        '54:0': 130,
        '55:0': 180,
    }
    for role in roles:
        base = 'Legend Sword' if role['build'] == 'berserk-barbarian' else 'Phase Blade'
        item = replace(
            facts(base),
            name='Lawbringer',
            runeword='Lawbringer',
            sockets=3,
            socket_contents='filled',
            filled_sockets=3,
            ethereal=base != 'Phase Blade',
            stats={
                k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
                for k, v in values.items()
            },
        )
        context = {'player_class': role['must']['all'][0]['value'], 'mercenary_type': role['mercenary_type']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, ctx=context, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert not evaluate(item, {**context, 'mercenary_type': 'Act 2 Might'}).annotations
        assert not evaluate(replace(item, base_code=facts('War Scepter').base_code)).annotations
        assert not evaluate(replace(item, rarity='magic')).annotations
        wrong = replace(item, stats={**item.stats, '198:5583': {'status': 'decoded', 'value': 20, 'unit': 'level'}})
        assert '198:5583' not in evaluate(wrong).annotations
        legend = replace(item, base_code=facts('Legend Sword').base_code)
        if role['mercenary_type'] == 'Act 5 Frenzy':
            assert not evaluate(legend).annotations
        else:
            assert set(evaluate(legend).annotations) == set(values)


def test_crescent_moon_caster_merc_does_not_receive_melee_or_player_bonuses():
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == ['Crescent Moon'] and r['id'].endswith('-merc-sword-tail')
    ]
    assert len(roles) == 1
    role = roles[0]
    context = {'player_class': 'Druid', 'mercenary_type': 'Act 3 Lightning'}
    values = {'334:0': 35, '147:0': 11}
    excluded = {'17:0': 220, '18:0': 220, '93:0': 20, '135:0': 25, '115:0': 1, '138:0': 2}
    item = replace(
        facts('Crystal Sword'),
        name='Crescent Moon',
        runeword='Crescent Moon',
        sockets=3,
        socket_contents='filled',
        filled_sockets=3,
        ethereal=True,
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **excluded}.items()},
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]

    def evaluate(candidate, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == set(values)
    for base in ('Legend Sword', 'Thresher', 'Berserker Axe'):
        assert not evaluate(replace(item, base_code=facts(base).base_code)).annotations
    assert not evaluate(item, {**context, 'mercenary_type': 'Act 2 Might'}).annotations
    assert not evaluate(replace(item, socket_contents='empty')).annotations
