from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def bundle():
    return build()


@pytest.mark.parametrize(
    ('name', 'base', 'values'),
    [
        ('Gore Rider', 'War Boots', {'135:0': 10, '136:0': 15, '141:0': 15, '96:0': 30}),
        ('Goblin Toe', 'Light Plated Boots', {'136:0': 25, '34:0': 1, '35:0': 1}),
        ('War Traveler', 'Battle Boots', {'80:0': 30, '96:0': 25, '0:0': 10, '3:0': 10, '21:0': 15, '22:0': 25}),
        ('String of Ears', 'Demonhide Sash', {'35:0': 10, '36:0': 10, '60:0': 6}),
        ("Nosferatu's Coil", 'Vampirefang Belt', {'0:0': 15, '138:0': 2, '150:0': 10, '60:0': 5, '93:0': 10}),
        ("Verdungo's Hearty Cord", 'Mithril Coil', {'36:0': 10, '3:0': 30, '74:0': 10, '99:0': 10}),
    ],
)
def test_zeal_melee_accessories_credit_native_attack_or_defensive_properties(bundle, name, base, values):
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-zeal-melee-accessory') and r['names'] == [name]]
    assert len(roles) == 1
    role = roles[0]
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})

    def evaluate(item, klass='Paladin'):
        context = {'player_class': klass}
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, roles, context)
        )

    assert set(evaluate(item).annotations) == set(values)
    for patch in ({'ethereal': True}, {'ethereal': None}, {'identified': False}, {'rarity': 'rare'}, {'sockets': 1}):
        assert not evaluate(replace(item, **patch)).annotations
    assert not evaluate(item, 'Sorceress').annotations
