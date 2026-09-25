from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'base', 'values'),
    [
        ('axe-weapon', 'Flying Axe', {'17:0': 150, '18:0': 150, '253:0': 10, '93:0': 20, '188:32': 2, '39:0': 20}),
        ('axe-offhand', 'Flying Axe', {'17:0': 150, '18:0': 150, '253:0': 10, '93:0': 20, '188:32': 2, '39:0': 20}),
        (
            'knife-weapon',
            'Flying Knife',
            {'17:0': 200, '18:0': 200, '253:0': 10, '188:32': 2, '19:0': 121, '62:0': 6, '198:4225': 5},
        ),
        (
            'knife-offhand',
            'Flying Knife',
            {'17:0': 200, '18:0': 200, '253:0': 10, '188:32': 2, '19:0': 121, '62:0': 6, '198:4225': 5},
        ),
        (
            'harpoon-weapon',
            'Winged Harpoon',
            {'17:0': 200, '18:0': 200, '253:0': 10, '93:0': 20, '188:32': 2, '60:0': 9},
        ),
    ],
)
def test_imbue_examples_keep_distinct_stat_combinations_and_slot_placement(suffix, base, values):
    profiles = build()['profiles']
    profile = next((p for p in profiles if p['id'] == f'double-throw-imbue-{suffix}'), None)
    assert profile is not None
    stats = {k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    stats['253:0']['unit'] = 'replenishment_rate'
    if '198:4225' in stats:
        stats['198:4225']['unit'] = 'percent_chance'
    item = replace(facts(base, 'rare'), ethereal=True, stats=stats)
    context = {'player_class': 'Barbarian'}
    assert assess_roles(item, [profile], context)[0]['rule_trace']['truth'] == 'true'
    for key in stats:
        changed = replace(item, stats={k: v for k, v in stats.items() if k != key})
        expected = 'partial' if key in ('253:0', '198:4225') else 'failed'
        assert assess_roles(changed, [profile], context)[0]['status'] == expected
    for changed in (
        replace(item, ethereal=False),
        replace(item, stats={**stats, '54:0': {'status': 'decoded', 'value': 1}}),
        replace(item, sockets=1),
    ):
        assert assess_roles(changed, [profile], context)[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='normal'), [profile], context)
    assert not any(p['id'] == 'double-throw-imbue-harpoon-offhand' for p in profiles)
