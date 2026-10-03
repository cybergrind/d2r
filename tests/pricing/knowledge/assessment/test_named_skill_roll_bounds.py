from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


ESCHUTA = Item(
    'Eldritch Orb',
    'unique',
    "Eschuta's Temper",
    ((83, 1, 3), (105, 0, 40), (329, 0, 20), (330, 0, 20), (1, 0, 30)),
    complete=True,
)
WEB = Item(
    'Unearthed Wand',
    'unique',
    "Death's Web",
    ((127, 0, 2), (336, 0, 50), (86, 0, 12), (138, 0, 12), (188, 17, 2)),
    complete=True,
)


@pytest.mark.parametrize(('template', 'stat', 'low', 'high'), [(ESCHUTA, 83, 1, 3), (WEB, 188, 1, 2)])
def test_named_price_contract_rejects_impossible_skill_roll(template, stat, low, high):
    for value, valid in ((low, True), (high, True), (low - 1, False), (high + 1, False)):
        item = replace(
            template, raw_stats=tuple((s, layer, value if s == stat else raw) for s, layer, raw in template.raw_stats)
        )
        contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
        assert (contract is not None) is valid, (value, gaps)
        if not valid:
            assert any(f'{stat}:' in gap for gap in gaps)


# Independently enumerated native unique property intervals, including Amazon
# weapon tabs: unique quality does not also roll the base's random auto-prefix.
INTERVALS = (
    ("Athena's Wrath", 83, 5, 1, 3),
    ('Valkyrie Wing', 83, 0, 1, 2),
    ("Death's Web", 188, 17, 1, 2),
    ("Seraph's Hymn", 188, 26, 1, 2),
    ('Jade Talon', 188, 49, 1, 2),
    ('Jade Talon', 188, 50, 1, 2),
    ('Shadow Dancer', 188, 49, 1, 2),
    ("Cerebus' Bite", 188, 41, 2, 4),
    ('Stoneraven', 188, 2, 1, 3),
    ("Demonhorn's Edge", 188, 32, 1, 3),
    ("Demonhorn's Edge", 188, 33, 1, 3),
    ("Demonhorn's Edge", 188, 34, 1, 3),
    ('Spirit Keeper', 83, 5, 1, 2),
    ('Alma Negra', 83, 3, 1, 2),
    ('Darkforce Spawn', 188, 16, 1, 3),
    ('Darkforce Spawn', 188, 17, 1, 3),
    ('Darkforce Spawn', 188, 18, 1, 3),
    ("Blood Raven's Charge", 188, 0, 2, 4),
    ('Thunderstroke', 188, 2, 2, 4),
    ('Boneflame', 83, 2, 2, 3),
    ('Wolfhowl', 188, 34, 2, 3),
    ("Templar's Might", 188, 25, 1, 2),
    ("Eschuta's Temper", 83, 1, 1, 3),
    ("Firelizard's Talons", 188, 50, 1, 3),
    ("Heaven's Light", 83, 3, 2, 3),
    ("Astreon's Iron Ward", 188, 24, 2, 4),
)


@pytest.mark.parametrize(('name', 'stat', 'layer', 'low', 'high'), INTERVALS)
def test_variable_named_skill_intervals(name, stat, layer, low, high):
    facts = normalize(ESCHUTA.capture())
    definition = catalog().named['unique', name]
    key = f'{stat}:{layer}'
    for value, valid in ((low, True), (high, True), (low - 1, False), (high + 1, False), (True, False), (1.5, False)):
        specimen = replace(facts, stats={key: {'status': 'decoded', 'value': value}})
        matching = [gap for gap in roll_gaps(specimen, definition) if key in gap]
        assert (not matching) is valid, (name, value, matching)
