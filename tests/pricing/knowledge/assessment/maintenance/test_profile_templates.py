from dataclasses import replace
from typing import Any

from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.policies.test_torch_tier import torch


def profile():
    from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile

    return expand_profile(
        {
            'id': 'torch-example',
            'template': 'unique_inventory_charm',
            'item': 'Hellfire Torch',
            'class': 'Sorceress',
            'build': 'example',
            'variant': 'Standard',
            'side': 'player',
            'slot': 'Charms',
            'source': {'review': 'Test native charm semantics'},
        }
    )


def sorceress_truth(item, role) -> str:
    rows: list[dict[str, Any]] = assess_roles(item, [role], {'player_class': 'Sorceress'})
    return rows[0]['rule_trace']['truth']


def test_torch_template_accepts_low_rolls_but_requires_the_correct_single_class():
    role = profile()
    for item in (torch(1, 10, 10), torch(1, 20, 20)):
        assert sorceress_truth(item, role) == 'true'
    for item in (torch(7, 20, 20), replace(torch(1, 20, 20), ethereal=True), replace(torch(1, 20, 20), sockets=1)):
        assert sorceress_truth(item, role) == 'false'
    mixed = replace(torch(1, 20, 20), stats={**torch(1, 20, 20).stats, '83:7': {'status': 'decoded', 'value': 3}})
    assert sorceress_truth(mixed, role) == 'false'


def test_unknown_class_capture_never_claims_the_class_bonus():
    role = profile()
    item = replace(torch(1, 10, 10), stats={}, capture_complete=False)
    assert sorceress_truth(item, role) == 'unknown'
