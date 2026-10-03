from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.named_flee import capture_gap
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('name', 'raw'),
    [
        ("Ume's Lament", 64),
        ('Steelgoad', 96),
        ('Howltusk', 33),
        ('The Face of Horror', 64),
        ('Rattlecage', 52),
        ('Lacerator', 64),
    ],
)
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_native_flee_roll_cannot_be_substituted_by_display_rounding(name, raw, offset):
    definition = catalog().named['unique', name]
    item = Item(definition['base_definition']['name'], 'unique', name, ((112, 0, raw + offset),), complete=True)
    assert (capture_gap(normalize(item.capture()), definition) is None) is (offset == 0)


def test_flee_decoded_percent_must_match_raw():
    definition = catalog().named['unique', 'Howltusk']
    facts = normalize(Item('Great Helm', 'unique', 'Howltusk', ((112, 0, 33),), complete=True).capture())
    facts = replace(facts, stats={'112:0': {**facts.stats['112:0'], 'value': 26}})
    assert capture_gap(facts, definition)


def test_no_native_flee_does_not_invent_an_obligation():
    definition = catalog().named['unique', 'Harlequin Crest']
    facts = normalize(Item('Shako', 'unique', 'Harlequin Crest', (), complete=True).capture())
    assert capture_gap(facts, definition) is None
