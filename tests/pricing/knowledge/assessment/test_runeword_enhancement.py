from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.runeword import definitions
from pricing.knowledge.assessment.mechanics.runeword_rolls import variable_roll_gaps
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('quality', 'total', 'valid'),
    [
        ('normal', 340, True),
        ('normal', 341, False),
        ('superior', 355, True),
        ('superior', 356, False),
        ('normal', 209, False),
        ('superior', 209, False),
        ('superior', 340.5, False),
    ],
)
def test_oath_damage_totals_account_for_superior_base(quality, total, valid):
    item = replace(
        facts('Balrog Blade', quality), stats={f'{stat}:0': {'status': 'decoded', 'value': total} for stat in (17, 18)}
    )
    gaps = variable_roll_gaps(item, definitions()['Oath'], 'weapon')
    enhancement = [gap for gap in gaps if '17:0' in gap or '18:0' in gap]
    assert bool(enhancement) is not valid


@pytest.mark.parametrize(
    ('quality', 'total', 'valid'),
    [
        ('normal', 290, True),
        ('normal', 291, False),
        ('superior', 305, True),
        ('superior', 306, False),
        ('superior', 199, False),
    ],
)
def test_stone_defense_totals_account_for_superior_base(quality, total, valid):
    item = replace(facts('Archon Plate', quality), stats={'16:0': {'status': 'decoded', 'value': total}})
    gaps = variable_roll_gaps(item, definitions()['Stone'], 'armor')
    enhancement = [gap for gap in gaps if '16:0' in gap]
    assert bool(enhancement) is not valid


@pytest.mark.parametrize(
    ('quality', 'total', 'valid'),
    [
        ('normal', 200, True),
        ('normal', 215, False),
        ('superior', 200, True),
        ('superior', 205, True),
        ('superior', 215, True),
        ('superior', 201, False),
        ('superior', 216, False),
        ('superior', True, False),
        ('normal', float('nan'), False),
    ],
)
def test_fixed_fortitude_defense_accepts_only_possible_quality_contributions(quality, total, valid):
    item = replace(facts('Archon Plate', quality), stats={'16:0': {'status': 'decoded', 'value': total}})
    gaps = variable_roll_gaps(item, definitions()['Fortitude'], 'armor')
    enhancement = [gap for gap in gaps if '16' in gap]
    assert bool(enhancement) is not valid
