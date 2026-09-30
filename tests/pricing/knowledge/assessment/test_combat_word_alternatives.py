from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'sockets', 'values', 'smite_excluded'),
    [
        ('Grief', 5, 5, {'111:0': 400, '93:0': 40, '141:0': 20, '115:0': 1, '116:0': 25}, {'141:0', '115:0', '116:0'}),
        ('Oath', 4, 4, {'17:0': 340, '18:0': 340, '93:0': 50, '147:0': 15, '121:0': 75, '123:0': 100}, set()),
        (
            'Unbending Will',
            3,
            6,
            {'17:0': 350, '18:0': 350, '93:0': 30, '188:32': 3, '0:0': 10, '3:0': 10, '34:0': 8},
            set(),
        ),
        (
            'Death',
            1,
            5,
            {'136:0': 50, '17:0': 385, '18:0': 385, '250:0': 0.5, '62:0': 7},
            {'17:0', '18:0', '250:0', '62:0'},
        ),
        (
            'Last Wish',
            2,
            6,
            {'136:0': 70, '151:98': 17, '198:5266': 10, '201:17099': 6, '17:0': 375, '18:0': 375, '115:0': 1},
            {'17:0', '18:0', '115:0'},
        ),
    ],
)
def test_melee_words_preserve_source_base_durability_and_smite_exclusions(name, count, sockets, values, smite_excluded):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-combat-word-alternative')]
    assert len(roles) == count
    for role in roles:
        base = next(b['name'] for b in metadata()['bases'].values() if b['code'] == role['base_codes'][0])
        item = replace(
            facts(base, 'normal', name),
            runeword=name,
            sockets=sockets,
            socket_contents='filled',
            stats={
                k: {
                    'status': 'decoded',
                    'value': v,
                    **({'unit': 'percent_chance'} if k.startswith(('198:', '201:')) else {}),
                }
                for k, v in values.items()
            },
        )
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        expected = set(values) - (smite_excluded if role['build'] == 'smite-paladin' else set())
        assert set(evaluate(item).annotations) == expected
        for change in (
            {'socket_contents': 'empty'},
            {'sockets': sockets - 1},
            {'runeword': None},
            {'base_code': facts('Crystal Sword').base_code},
        ):
            assert not evaluate(replace(item, **change)).annotations
        eth = replace(item, ethereal=True)
        assert not evaluate(eth).annotations
        durable = replace(eth, stats={**eth.stats, '152:0': {'status': 'decoded', 'value': 1}})
        assert set(evaluate(durable).annotations) == (expected if name in ('Oath', 'Death') else set())
        if name == 'Last Wish':
            bad = replace(
                item, stats={**item.stats, '198:5266': {'status': 'decoded', 'value': 10, 'unit': 'skill_level'}}
            )
            assert '198:5266' not in evaluate(bad).annotations
