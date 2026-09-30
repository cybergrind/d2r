from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values', 'excluded'),
    [
        (
            'Lacerator',
            'Winged Axe',
            2,
            {'17:0': 210, '18:0': 210, '93:0': 30, '135:0': 33, '198:4227': 33, '253:0': 25},
            set(),
        ),
        (
            'Warshrike',
            'Winged Knife',
            2,
            {'17:0': 250, '18:0': 250, '93:0': 30, '156:0': 50, '141:0': 50, '253:0': 30},
            set(),
        ),
        ("Demon's Arch", 'Balrog Spear', 2, {'17:0': 210, '18:0': 210, '93:0': 30, '60:0': 12, '253:0': 30}, set()),
        ('Gimmershred', 'Flying Axe', 2, {'17:0': 210, '18:0': 210, '93:0': 30, '254:0': 60}, set()),
        ('Wraith Flight', 'Ghost Glaive', 2, {'17:0': 190, '18:0': 190, '60:0': 13, '138:0': 15, '253:0': 40}, set()),
        (
            "Titan's Revenge",
            'Ceremonial Javelin',
            2,
            {'83:0': 2, '188:2': 2, '96:0': 30, '0:0': 20, '2:0': 20, '17:0': 200, '18:0': 200, '60:0': 9, '253:0': 30},
            set(),
        ),
        (
            'Thunderstroke',
            'Matriarchal Javelin',
            2,
            {'188:2': 4, '334:0': 15, '93:0': 15, '17:0': 200, '18:0': 200, '107:20': 3},
            {'107:20'},
        ),
    ],
)
def test_throwing_uniques_distinguish_quantity_recovery_ethereal_and_skill_damage(name, base, count, values, excluded):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-named-throwing-alternative')
    ]
    assert len(roles) == count
    stats = {
        k: {
            'status': 'decoded',
            'value': v,
            **(
                {'unit': 'percent_chance'}
                if k.startswith('198:')
                else {'unit': 'replenishment_rate'}
                if k == '253:0'
                else {}
            ),
        }
        for k, v in values.items()
    }
    item = replace(facts(base, 'unique', name), ethereal=name == 'Wraith Flight', stats=stats)
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        expected = set(values) - excluded
        assert set(evaluate(item).annotations) == expected
        eth = replace(item, ethereal=True)
        assert set(evaluate(eth).annotations) == (set() if name == 'Thunderstroke' else expected)
        if name == 'Wraith Flight':
            assert not evaluate(replace(item, ethereal=False)).annotations
        for change in ({'sockets': 1}, {'socket_contents': 'filled'}, {'rarity': 'rare'}):
            assert not evaluate(replace(item, **change)).annotations
        if '253:0' in values:
            bad = replace(item, stats={**item.stats, '253:0': {'status': 'decoded', 'value': 30, 'unit': 'seconds'}})
            assert not evaluate(bad).annotations
        if name == 'Gimmershred':
            outcome = assess_role_results(eth, [role], context)[0]
            assert outcome.status == 'partial'
            assert any('Throwing Mastery' in reason for reason in outcome.missing)
        if name == "Titan's Revenge":
            upgraded = replace(item, base_code=facts('Matriarchal Javelin').base_code)
            assert set(evaluate(upgraded).annotations) == expected
