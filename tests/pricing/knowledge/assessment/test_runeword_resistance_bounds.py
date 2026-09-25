from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.runeword import definitions
from pricing.knowledge.assessment.mechanics.runeword_rolls import variable_roll_gaps
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('base', 'value', 'valid'),
    [('Monarch', 70, True), ('Monarch', 71, False), ('Sacred Targe', 115, True), ('Sacred Targe', 116, False)],
)
def test_sanctuary_resistance_total_includes_only_possible_base_bonus(base, value, valid):
    item = replace(
        facts(base),
        stats={
            f'{s}:0': {'status': 'decoded', 'value': v} for s, v in [(16, 150), *[(r, value) for r in (39, 41, 43, 45)]]
        },
    )
    gaps = variable_roll_gaps(item, definitions()['Sanctuary'], 'shield')
    assert (not gaps) is valid


def test_all_resistance_recipe_cannot_have_different_element_rolls():
    item = replace(
        facts('Archon Plate'),
        stats={f'{r}:0': {'status': 'decoded', 'value': 30 if r == 39 else 25} for r in (39, 41, 43, 45)},
    )
    assert variable_roll_gaps(item, definitions()['Fortitude'], 'armor')


@pytest.mark.parametrize(('word', 'stat'), [('Cure', 45), ('Ground', 41), ('Hearth', 43), ('Temper', 39)])
def test_helm_recipe_resistance_includes_socketed_rune(word, stat):
    item = replace(facts('Bone Visage'), stats={'16:0': {'status': 'decoded', 'value': 80}})
    # Some recipes also roll absorption; isolate the resistance checks here.
    from pricing.knowledge.assessment.mechanics.runeword_rolls import resistance_gaps

    for value in (40, 60):
        captured = replace(item, stats={**item.stats, f'{stat}:0': {'status': 'decoded', 'value': value}})
        assert not resistance_gaps(captured, definitions()[word], 'helm')
    for value in (10, 30, 39, 61):
        captured = replace(item, stats={**item.stats, f'{stat}:0': {'status': 'decoded', 'value': value}})
        assert resistance_gaps(captured, definitions()[word], 'helm')


@pytest.mark.parametrize(
    ('base', 'resists', 'valid'),
    [
        ('Monarch', (0, 35, 35, 35), True),
        ('Monarch', (0, 36, 35, 35), False),
        ('Sacred Targe', (45, 80, 80, 80), True),
        ('Sacred Targe', (44, 80, 80, 80), False),
        ('Sacred Targe', (46, 81, 81, 81), False),
    ],
)
def test_spirit_fixed_rune_resistance_and_base_bonus_agree(base, resists, valid):
    from pricing.knowledge.assessment.mechanics.runeword_rolls import resistance_gaps

    item = replace(
        facts(base),
        stats={f'{s}:0': {'status': 'decoded', 'value': v} for s, v in zip((39, 41, 43, 45), resists, strict=True)},
    )
    assert (not resistance_gaps(item, definitions()['Spirit'], 'shield')) is valid


def test_rhyme_fixed_resistance_is_not_an_arbitrary_roll():
    from pricing.knowledge.assessment.mechanics.runeword_rolls import resistance_gaps

    for value in (25, 26):
        item = replace(facts('Bone Shield'), stats={'39:0': {'status': 'decoded', 'value': value}})
        assert (not resistance_gaps(item, definitions()['Rhyme'], 'shield')) is (value == 25)
    # Omitted fields are not inferred to be zero by this bounds-only check.
    assert not resistance_gaps(facts('Bone Shield'), definitions()['Rhyme'], 'shield')
