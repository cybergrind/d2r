from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


SHAFT = Item(
    'Mesh Armor',
    'unique',
    'Shaftstop',
    ((31, 0, 642), (16, 0, 200), (32, 0, 250), (36, 0, 30), (7, 0, 60 * 256)),
    complete=True,
)


@pytest.mark.parametrize(('defense', 'valid'), [(641, False), (642, True), (643, False), (650, False)])
def test_shaftstop_total_matches_observed_ed(defense, valid):
    item = replace(SHAFT, raw_stats=tuple((s, p, defense if s == 31 else v) for s, p, v in SHAFT.raw_stats))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'armor')
    assert (contract is not None) is valid, gaps


@pytest.mark.parametrize(
    ('base', 'defense', 'valid'),
    [
        ('Templar Coat', 789, True),
        ('Templar Coat', 788, False),
        ('Hellforge Plate', 1208, True),
        ('Hellforge Plate', 1209, False),
    ],
)
def test_guardian_angel_original_and_upgrade_defense(base, defense, valid):
    from pricing.knowledge.assessment.mechanics.enhanced_defense import capture_gap
    from pricing.knowledge.definition_store import catalog

    item = Item(base, 'unique', 'Guardian Angel', ((31, 0, defense), (16, 0, 187)), complete=True)
    assert (
        capture_gap(normalize(item.capture()), catalog().named['unique', 'Guardian Angel'], 'armor') is None
    ) is valid


@pytest.mark.parametrize(('defense', 'valid'), [(348, False), (349, True), (399, True), (400, False)])
def test_crown_of_ages_flat_bonus_is_not_scaled_by_enhanced_defense(defense, valid):
    from pricing.knowledge.assessment.mechanics.enhanced_defense import capture_gap
    from pricing.knowledge.definition_store import catalog

    item = Item('Corona', 'unique', 'Crown of Ages', ((31, 0, defense), (16, 0, 50)), complete=True)
    assert (capture_gap(normalize(item.capture()), catalog().named['unique', 'Crown of Ages'], 'helm') is None) is valid
