from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('Arachnid Mesh', 'Spiderweb Sash', {'127:0': 1, '105:0': 20, '77:0': 5, '150:0': 10}),
    ('Goldwrap', 'Heavy Belt', {'80:0': 30, '79:0': 50, '93:0': 10}),
    ("Thundergod's Vigor", 'War Belt', {'42:0': 10, '145:0': 20, '0:0': 20, '3:0': 20}),
]


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(('name', 'base', 'values'), CASES)
def test_zeal_belts_preserve_cast_attack_and_absorb_distinctions(bundle, name, base, values):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-utility-belt') and r['names'] == [name]]
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    item = replace(facts(base, 'unique', name), stats=stats)

    def evaluate(item, context):
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item, {'player_class': 'Paladin'}).annotations) == set(values)
    for context in ({'player_class': 'Necromancer'}, {}):
        assert not evaluate(item, context).annotations
    for patch in ({'sockets': 1}, {'ethereal': True}, {'identified': False}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **patch), {'player_class': 'Paladin'}).annotations
