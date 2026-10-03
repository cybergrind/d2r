from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


GRIFFON = Item(
    'Diadem',
    'unique',
    "Griffon's Eye",
    ((31, 0, 260), (105, 0, 25), (127, 0, 1), (330, 0, 15), (334, 0, 20)),
    complete=True,
)


@pytest.mark.parametrize(('ethereal', 'values'), [(False, (149, 150, 260, 261)), (True, (174, 175, 290, 291))])
def test_flat_defense_uses_base_plus_bonus_not_bonus_alone(ethereal, values):
    for index, defense in enumerate(values):
        item = replace(
            GRIFFON,
            ethereal=ethereal,
            raw_stats=tuple((s, p, defense if s == 31 else v) for s, p, v in GRIFFON.raw_stats),
        )
        contract, gaps = NamedHandler().contract(normalize(item.capture()), 'helm')
        assert (contract is not None) is (index in (1, 2)), gaps


@pytest.mark.parametrize(('defense', 'valid'), [(299, False), (300, True), (350, True), (351, False)])
def test_metalgrid_has_no_armor_base_to_add(defense, valid):
    from pricing.knowledge.assessment.mechanics.flat_defense import capture_gap
    from pricing.knowledge.definition_store import catalog

    item = Item('Amulet', 'unique', 'Metalgrid', ((31, 0, defense),), complete=True)
    assert (capture_gap(normalize(item.capture()), catalog().named['unique', 'Metalgrid'], 'jewelry') is None) is valid


@pytest.mark.parametrize(
    ('name', 'base', 'low', 'high'),
    [
        ("Kira's Guardian", 'Tiara', 90, 170),
        ("Ormus' Robes", 'Dusk Shroud', 371, 487),
        ('Steelrend', 'Ogre Gauntlets', 232, 281),
        ('Giant Skull', 'Bone Visage', 350, 477),
    ],
)
def test_flat_armor_bounds_follow_each_base(name, base, low, high):
    from pricing.knowledge.assessment.mechanics.flat_defense import capture_gap
    from pricing.knowledge.definition_store import catalog

    for defense, valid in ((low - 1, False), (low, True), (high, True), (high + 1, False)):
        facts = normalize(Item(base, 'unique', name, ((31, 0, defense),), complete=True).capture())
        assert (capture_gap(facts, catalog().named['unique', name], 'helm') is None) is valid


def test_nonethereal_upgrade_uses_upgraded_base_defense():
    from pricing.knowledge.assessment.mechanics.flat_defense import capture_gap
    from pricing.knowledge.definition_store import catalog

    # Greyform's fixed20 defense combines with Dusk Shroud's361..467 base.
    definition = catalog().named['unique', 'Greyform']
    for defense, valid in ((380, False), (381, True), (487, True), (488, False)):
        facts = normalize(Item('Dusk Shroud', 'unique', 'Greyform', ((31, 0, defense),), complete=True).capture())
        assert (capture_gap(facts, definition, 'armor') is None) is valid
