from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_aura_recipe_tail import recipe


def test_mosaic_offhand_keeps_charge_retention_and_requires_the_other_equipped_claw():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == ['Mosaic'] and r['id'].endswith('-aura-recipe')]
    assert len(roles) == 1
    role = roles[0]
    values = {'188:50': 2, '200:0': 50, '329:0': 15, '330:0': 15, '331:0': 15}
    item = recipe('Mosaic', 'Greater Talons', 3, {**values, '17:0': 250, '18:0': 250, '93:0': 20, '60:0': 7})
    context = {'player_class': 'Assassin', 'player_equipment': {'weapon': item}}
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    result = StatsEvaluator().evaluate(item, configs, context, role_outcomes=assess_role_results(item, roles, context))
    assert set(result.annotations) == set(values)
    assert assess_roles(item, roles, context)[0]['dependencies'][0]['status'] == 'true'
    assert (
        assess_roles(item, roles, {'player_class': 'Assassin', 'player_items': ['Mosaic', 'Mosaic']})[0][
            'dependencies'
        ][0]['status']
        == 'unknown'
    )
    for other in (None, replace(item, runeword='Chaos'), replace(item, ethereal=True), replace(item, sockets=2)):
        assert (
            assess_roles(item, roles, {**context, 'player_equipment': {'weapon': other}})[0]['dependencies'][0][
                'status'
            ]
            != 'true'
        )
    assert assess_roles(replace(item, ethereal=True), roles, context)[0]['status'] == 'failed'
