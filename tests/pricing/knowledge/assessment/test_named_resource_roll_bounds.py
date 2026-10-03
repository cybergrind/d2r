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


@pytest.mark.parametrize(('energy', 'valid'), [(20, True), (30, True), (19, False), (31, False)])
def test_price_comparison_requires_legal_energy(energy, valid):
    item = replace(ESCHUTA, raw_stats=tuple((s, p, energy if s == 1 else v) for s, p, v in ESCHUTA.raw_stats))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
    assert (contract is not None) is valid, gaps


INTERVALS = (
    ('unique', "Andariel's Visage", 0, 25, 30),
    ('unique', "Eschuta's Temper", 1, 20, 30),
    ('unique', "Nightwing's Veil", 2, 10, 20),
    ('unique', "Verdungo's Hearty Cord", 3, 30, 40),
    ('unique', 'Waterwalk', 7, 45, 65),
    ('set', "Trang-Oul's Girth", 9, 25, 50),
    ('unique', "Verdungo's Hearty Cord", 11, 100, 120),
    ('unique', "Ormus' Robes", 27, 10, 15),
    ('unique', 'Carrion Wind', 32, 100, 160),
    ('unique', "The Gladiator's Bane", 34, 15, 20),
    ('unique', 'Manald Heal', 74, 5, 8),
    ('unique', 'Chromatic Ire', 76, 20, 25),
    ('unique', 'Entropy Locket', 77, 10, 15),
    ('unique', 'Stoutnail', 78, 3, 10),
    ('unique', "Death's Web", 86, 7, 12),
    ('unique', 'The Eye of Etlich', 89, 1, 5),
    ('unique', "Gheed's Wager", 96, 10, 20),
    ('unique', 'Sparking Mail', 128, 10, 14),
    ('unique', "Death's Web", 138, 7, 12),
    ('unique', 'Ethereal Edge', 139, 5, 10),
    ('unique', 'Spirit Keeper', 145, 9, 14),
    ('unique', "Nightwing's Veil", 149, 5, 9),
    ('unique', 'Entropy Locket', 357, 5, 10),
    ('unique', 'Sling', 358, 3, 5),
    ('unique', "Protector's Stone", 366, 5, 10),
)


@pytest.mark.parametrize(('quality', 'name', 'stat', 'low', 'high'), INTERVALS)
def test_independent_scalar_intervals(quality, name, stat, low, high):
    facts = normalize(ESCHUTA.capture())
    definition = catalog().named[quality, name]
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
        gaps = [g for g in roll_gaps(specimen, definition) if f' {key} ' in g]
        assert (not gaps) is valid, (name, value, gaps)


def test_socket_dexterity_is_subtracted_before_native_bounds():
    from pricing.knowledge.assessment.handlers.socket_fillers import compare_named_sockets
    from tests.pricing.knowledge.assessment.item_bank.models import SocketItem

    definition = catalog().named['unique', "Nightwing's Veil"]
    item = Item(
        'Spired Helm',
        'unique',
        "Nightwing's Veil",
        ((2, 0, 30), (194, 0, 1)),
        sockets=1,
        socket_contents='filled',
        socket_items=(SocketItem('Ko Rune', (), complete=True),),
        complete=True,
    )
    facts = normalize(item.capture())
    comparison = compare_named_sockets(facts, definition, 'helm')
    assert comparison is not None
    assert comparison.facts.stats['2:0']['value'] == 20
    assert facts.stats['2:0']['value'] == 30
    assert not any(' 2:0 ' in gap for gap in roll_gaps(comparison.facts, definition))
    assert any(' 2:0 ' in gap for gap in roll_gaps(facts, definition))
    invalid = normalize(replace(item, raw_stats=((2, 0, 31), (194, 0, 1))).capture())
    assert compare_named_sockets(invalid, definition, 'helm') is None
