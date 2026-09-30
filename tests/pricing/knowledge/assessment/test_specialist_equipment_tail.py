from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'values', 'excluded'),
    [
        (
            "Arioc's Needle",
            'Hyperion Spear',
            {'127:0': 4, '17:0': 230, '18:0': 230, '141:0': 50, '115:0': 1, '93:0': 30},
            {'93:0'},
        ),
        (
            "Tyrael's Might",
            'Sacred Armor',
            {
                '153:0': 1,
                '96:0': 20,
                '39:0': 30,
                '41:0': 30,
                '43:0': 30,
                '45:0': 30,
                '0:0': 30,
                '121:0': 100,
                '16:0': 150,
            },
            set(),
        ),
        (
            'Shadow Dancer',
            'Myrmidon Greaves',
            {'188:49': 2, '99:0': 30, '96:0': 30, '2:0': 25, '16:0': 100, '188:50': 2},
            {'188:50'},
        ),
    ],
)
def test_specialist_equipment_distinguishes_casting_kicks_and_native_durability(name, base, values, excluded):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == [name] and r['id'].endswith('-specialist-equipment-alternative')
    ]
    assert len(roles) == 1
    role = roles[0]
    context = {'player_class': role['must']['all'][0]['value']}
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(values) - excluded
    assert set(evaluate(replace(item, ethereal=True)).annotations) == (
        set(values) - excluded if name == "Arioc's Needle" else set()
    )
    for change in ({'base_code': facts('Cap').base_code}, {'sockets': 3}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **change)).annotations
