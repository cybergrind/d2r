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
            'Bloodpact Shard',
            'Mithral Point',
            {'127:0': 1, '105:0': 30, '76:0': 15, '107:378': 3, '107:380': 3, '107:382': 3, '80:0': 35, '150:0': 25},
            {'150:0'},
        ),
        (
            'Earthshaker',
            'Battle Hammer',
            {'188:42': 3, '93:0': 30, '17:0': 180, '18:0': 180, '81:0': 1},
            {'81:0', '93:0', '17:0', '18:0'},
        ),
        (
            'Measured Wrath',
            'Burnt Text',
            {
                '83:7': 1,
                '105:0': 25,
                '107:394': 3,
                '107:398': 3,
                '107:376': 3,
                '3:0': 20,
                '86:0': 5,
                '39:0': 30,
                '41:0': 30,
                '43:0': 30,
                '45:0': 30,
                '16:0': 180,
            },
            set(),
        ),
        ('The Rising Sun', 'Amulet', {'126:1': 2, '235:0': 0.75, '74:0': 10, '48:0': 24, '49:0': 48}, {'49:0', '48:0'}),
        ("Horazon's Countenance", 'Demonhead', {'83:7': 1, '0:0': 20, '35:0': 10, '76:0': 5}, {'76:0'}),
        (
            "Horazon's Dominion",
            'Russet Armor',
            {'9:0': 100, '43:0': 25, '39:0': 25, '41:0': 25, '16:0': 100, '188:56': 2, '45:0': 25},
            {'45:0', '188:56'},
        ),
        ("Horazon's Legacy", 'Mirrored Boots', {'96:0': 30, '0:0': 15, '2:0': 15, '37:0': 30, '153:0': 1}, set()),
    ],
)
def test_caster_remainder_distinguishes_skill_element_and_conditional_set_stats(name, base, values, excluded):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-remainder-alternative')
    ]
    assert len(roles) == 1
    role = roles[0]
    context = {'player_class': role['must']['all'][0]['value']}
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]
    item = replace(
        facts(base, 'set' if name.startswith("Horazon's") else 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(values) - excluded
    assert set(evaluate(replace(item, ethereal=True)).annotations) == (
        set(values) - excluded if name in ('Bloodpact Shard', 'Earthshaker') else set()
    )
    for change in ({'base_code': facts('Cap').base_code}, {'sockets': 3}, {'rarity': 'rare'}):
        assert not evaluate(replace(item, **change)).annotations
