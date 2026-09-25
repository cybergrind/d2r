from dataclasses import replace

import pytest

from pricing.knowledge.assessment.roles.charges import charge_availability
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def charge(remaining):
    return {
        'status': 'decoded',
        'value': remaining,
        'unit': 'charges_remaining',
        'charges': {'remaining': remaining, 'maximum': 20},
    }


@pytest.mark.parametrize('remaining', [0, 1])
def test_conflicting_charge_row_cannot_prove_available_or_exhausted(remaining):
    item = replace(
        facts('Tyrant Club', 'unique', 'Demon Limb'),
        stats={'204:3351': charge(remaining)},
        gaps=['Duplicate native stat 204:3351.'],
    )
    assert charge_availability(item, 52, 1) == ('unknown', [])


def test_independent_valid_charge_level_can_establish_availability():
    item = replace(
        facts('Amulet', 'rare'),
        stats={'204:3467': charge(1), '204:3468': charge(2)},
        gaps=['Duplicate native stat 204:3467.'],
    )
    assert charge_availability(item, 54, 1) == ('true', [{'level': 12, 'remaining': 2, 'maximum': 20}])
