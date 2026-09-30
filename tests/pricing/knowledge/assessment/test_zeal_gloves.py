from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('Laying of Hands', 'Bramble Mitts', 'set', {'93:0': 20, '121:0': 350, '39:0': 50}),
    ("Dracul's Grasp", 'Vampirebone Gloves', 'unique', {'198:5258': 5, '135:0': 25, '0:0': 10, '86:0': 5, '60:0': 7}),
    ("Trang-Oul's Claws", 'Heavy Bracers', 'set', {'105:0': 20, '43:0': 30}),
    ('Bloodfist', 'Heavy Gloves', 'unique', {'7:0': 40, '99:0': 30, '93:0': 10, '21:0': 5}),
    ('Chance Guards', 'Chain Gloves', 'unique', {'80:0': 25, '79:0': 200, '19:0': 25}),
    ('Lava Gout', 'Battle Gauntlets', 'unique', {'93:0': 20, '39:0': 24, '118:0': 1, '198:3338': 2}),
]


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(('name', 'base', 'quality', 'values'), CASES)
def test_zeal_gloves_native_recipients_and_proc_units(bundle, name, base, quality, values):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-gloves') and r['names'] == [name]]
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    stats = {
        k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
        for k, v in values.items()
    }
    item = replace(facts(base, quality, name), stats=stats)

    def evaluate(item, context):
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item, {'player_class': 'Paladin'}).annotations) == set(values)
    for context in ({'player_class': 'Necromancer'}, {}):
        assert not evaluate(item, context).annotations
    for patch in ({'sockets': 1}, {'ethereal': True}, {'identified': False}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **patch), {'player_class': 'Paladin'}).annotations
    for key in (key for key in values if key.startswith('198:')):
        incorrect = {**stats, key: {**stats[key], 'unit': 'skill_level'}}
        assert key not in evaluate(replace(item, stats=incorrect), {'player_class': 'Paladin'}).annotations
