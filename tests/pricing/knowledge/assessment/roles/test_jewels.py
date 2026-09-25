from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role_id', 'resistance', 'side', 'recipient'),
    [
        ('lightning-standard-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('lightning-mf-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('blizzard-standard-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('blizzard-set-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('hammer-standard-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('hammer-ubers-ias-fire-jewel', 39, 'merc', "Andariel's Visage"),
        ('hammer-ubers-ias-lightning-jewel', 41, 'player', "Guillaume's Face"),
    ],
)
def test_jewel_requires_speed_resistance_and_correct_recipient_context(role_id, resistance, side, recipient):
    p = next(p for p in build()['profiles'] if p['id'] == role_id)
    item = replace(
        facts('Jewel', 'magic'),
        stats={'93:0': {'status': 'decoded', 'value': 15}, f'{resistance}:0': {'status': 'decoded', 'value': 30}},
    )
    role = assess_roles(item, [p])[0]
    assert role['rule_trace']['truth'] == 'true'
    assert role['status'] == 'partial'
    assert role['dependencies'][0]['status'] == 'unknown'
    assert all(x['status'] == 'true' for x in role['preferences'])
    context = {'mercenary_items' if side == 'merc' else 'player_items': [recipient]}
    assert assess_roles(item, [p], context)[0]['dependencies'][0]['status'] == 'true'
    wrong = {'player_items' if side == 'merc' else 'mercenary_items': [recipient]}
    assert assess_roles(item, [p], wrong)[0]['dependencies'][0]['status'] == 'unknown'
    assert assess_roles(replace(item, stats={'93:0': {'status': 'decoded', 'value': 15}}), [p])[0]['status'] == 'failed'
    assert assess_roles(replace(item, stats={}, capture_complete=False), [p])[0]['rule_trace']['truth'] == 'unknown'
    assert assess_roles(replace(item, rarity='rare'), [p]) == []
