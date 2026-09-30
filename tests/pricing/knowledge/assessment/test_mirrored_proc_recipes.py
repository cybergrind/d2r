from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'sockets', 'values'),
    [
        (
            'Rift',
            'War Scepter',
            4,
            {
                '198:15696': 20,
                '195:4117': 16,
                '52:0': 160,
                '53:0': 250,
                '48:0': 60,
                '49:0': 180,
                '114:0': 38,
                '0:0': 10,
                '1:0': 10,
                '2:0': 20,
                '3:0': 10,
                '119:0': 20,
            },
        ),
        (
            'Destruction',
            'Phase Blade',
            5,
            {
                '198:14679': 5,
                '195:3094': 15,
                '198:15628': 23,
                '17:0': 350,
                '18:0': 350,
                '52:0': 100,
                '53:0': 180,
                '136:0': 20,
                '141:0': 20,
                '62:0': 7,
                '115:0': 1,
                '2:0': 10,
            },
        ),
    ],
)
def test_mirrored_experimental_proc_recipes_do_not_leak_to_echoing(name, base, sockets, values):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-experimental-proc-recipe')
    ]
    assert len(roles) == 1
    role = roles[0]
    assert role['build'] == 'mirrored-blades-warlock-guide'
    assert 'Experimental' in role['role']
    item = replace(
        facts(base),
        name=name,
        runeword=name,
        sockets=sockets,
        socket_contents='filled',
        filled_sockets=sockets,
        stats={
            k: {
                'status': 'decoded',
                'value': v,
                **({'unit': 'percent_chance'} if k.startswith(('195:', '198:')) else {}),
            }
            for k, v in values.items()
        },
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    context = {'player_class': 'Warlock'}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, roles, context)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(replace(item, ethereal=True)).annotations
    assert not evaluate(replace(item, rarity='rare')).annotations
    assert not evaluate(replace(item, sockets=sockets - 1)).annotations
    assert not evaluate(
        replace(item, base_code=facts('Crystal Sword' if name == 'Rift' else 'War Scepter').base_code)
    ).annotations
    for key in values:
        if key.startswith(('195:', '198:')):
            wrong = replace(
                item, stats={**item.stats, key: {'status': 'decoded', 'value': values[key], 'unit': 'level'}}
            )
            assert key not in evaluate(wrong).annotations
    assert not any(k.startswith('197:') for k in role['important_stats'])
    assert all(r['build'] != 'echoing-strike-warlock-guide' for r in bundle['profiles'] if r.get('names') == [name])
