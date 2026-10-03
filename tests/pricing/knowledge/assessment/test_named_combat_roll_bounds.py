from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


SERAPH = Item(
    'Amulet',
    'unique',
    "Seraph's Hymn",
    ((127, 0, 2), (188, 26, 2), (121, 0, 50), (122, 0, 50), (123, 0, 250), (124, 0, 250), (89, 0, 2)),
    complete=True,
)


@pytest.mark.parametrize(('stat', 'low', 'high'), [(121, 25, 50), (122, 25, 50), (123, 150, 250), (124, 150, 250)])
def test_seraph_combat_modifiers_gate_exact_comparisons(stat, low, high):
    for value, valid in ((low, True), (high, True), (low - 1, False), (high + 1, False)):
        item = replace(SERAPH, raw_stats=tuple((s, p, value if s == stat else v) for s, p, v in SERAPH.raw_stats))
        contract, gaps = NamedHandler().contract(normalize(item.capture()), 'jewelry')
        assert (contract is not None) is valid, (stat, value, gaps)


@pytest.mark.parametrize(
    ('name', 'stat', 'low', 'high'),
    [
        ('Raven Frost', 19, 150, 250),
        ('Stone Crusher', 111, 10, 30),
        ("Nord's Tenderizer", 119, 150, 180),
        ('Goldstrike Arch', 121, 100, 200),
        ('Rusthandle', 122, 50, 60),
        ('Black Hades', 123, 200, 250),
        ('Gravepalm', 124, 100, 200),
        ("Nord's Tenderizer", 134, 2, 4),
    ],
)
def test_native_combat_intervals(name, stat, low, high):
    facts = normalize(SERAPH.capture())
    definition = catalog().named['unique', name]
    key = f'{stat}:0'
    for value, valid in (
        (low, True),
        (high, True),
        (low - 1, False),
        (high + 1, False),
        (True, False),
        (low + 0.5, False),
    ):
        specimen = replace(facts, stats={key: {'status': 'decoded', 'value': value}})
        errors = [g for g in roll_gaps(specimen, definition) if f' {key} ' in g]
        assert (not errors) is valid, (name, value, errors)


def test_blunt_base_bonus_is_not_part_of_the_native_undead_roll():
    item = Item('Grand Scepter', 'unique', 'Rusthandle', ((122, 0, 60),), complete=True)
    facts = normalize(item.capture())
    assert facts.stats['122:0']['value'] == 60
    definition = catalog().named['unique', 'Rusthandle']
    assert not any(' 122:0 ' in g for g in roll_gaps(facts, definition))
    invalid = normalize(replace(item, raw_stats=((122, 0, 110),)).capture())
    assert any(' 122:0 ' in g for g in roll_gaps(invalid, definition))
