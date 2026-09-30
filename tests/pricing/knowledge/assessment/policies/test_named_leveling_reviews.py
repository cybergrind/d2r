from dataclasses import replace

from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_strong_leveling_weapon_is_highlighted_independently_from_trade():
    uses = assess_leveling(facts('Maul', 'unique', 'Bonesnap'))
    assert any(use['tier'] == 'high' and 'attacks' in use['archetypes'] for use in uses)
    assert next(use for use in uses if use['tier'] == 'high')['required_level'] == 24


def test_mercenary_leveling_use_keeps_beneficiary_and_ethereal_variant():
    uses = assess_leveling(replace(facts('Fuscina', 'unique', 'Kelpie Snare'), ethereal=True))
    assert any(use['side'] == 'merc' and use['tier'] == 'high' for use in uses)


def test_unrecommended_item_does_not_print_negative_leveling_boilerplate():
    assert assess_leveling(facts('Legendary Mallet', 'unique', 'Stone Crusher')) == []
