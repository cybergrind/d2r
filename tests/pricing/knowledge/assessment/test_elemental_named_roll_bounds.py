from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


FATHOM = Item(
    'Dimensional Shard',
    'unique',
    "Death's Fathom",
    (
        (83, 1, 3),
        (331, 0, 30),
        (105, 0, 20),
        (39, 0, 40),
        (41, 0, 40),
    ),
    complete=True,
)


@pytest.mark.parametrize(('cold', 'valid'), [(15, True), (30, True), (14, False), (31, False), (40, False)])
def test_empty_fathom_comparison_requires_a_legal_native_cold_roll(cold, valid):
    item = replace(FATHOM, raw_stats=tuple((s, p, cold if s == 331 else v) for s, p, v in FATHOM.raw_stats))
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
    assert (contract is not None) is valid, gaps
    if not valid:
        assert any('331:0' in gap and '15-30' in gap for gap in gaps)


@pytest.mark.parametrize(
    ('name', 'stat', 'low', 'high'),
    [
        ("Eschuta's Temper", 329, 10, 20),
        ("Eschuta's Temper", 330, 10, 20),
        ("Nightwing's Veil", 331, 8, 15),
        ("Ormus' Robes", 329, 10, 15),
        ("Ormus' Robes", 330, 10, 15),
        ("Ormus' Robes", 331, 10, 15),
        ("Griffon's Eye", 334, 15, 20),
        ("Death's Web", 336, 40, 50),
    ],
)
def test_native_elemental_damage_and_pierce_intervals(name, stat, low, high):
    # This isolates the scalar contract; unrelated missing properties are not ignored
    # by NamedHandler, and are deliberately not asserted by this boundary test.
    definition = catalog().named['unique', name]
    facts = normalize(FATHOM.capture())
    key = f'{stat}:0'
    for value, valid in (
        (low, True),
        (high, True),
        (low - 1, False),
        (high + 1, False),
        (True, False),
        (low + 0.5, False),
    ):
        changed = replace(facts, stats={key: {'status': 'decoded', 'value': value}})
        matching = [g for g in roll_gaps(changed, definition) if key in g]
        assert (not matching) is valid, (name, value, matching)


def test_known_facet_subtraction_preserves_a_valid_native_roll():
    from pricing.knowledge.assessment.mechanics.intrinsic_socket_rolls import intrinsic_socket_rolls
    from tests.pricing.knowledge.assessment.item_bank.models import SocketItem

    facet = SocketItem('Jewel', ((331, 0, 5), (335, 0, 5)), complete=True, name='Rainbow Facet', unique_table_id=393)
    item = replace(
        FATHOM,
        sockets=1,
        socket_contents='filled',
        socket_items=(facet,),
        raw_stats=(*((s, p, 35 if s == 331 else v) for s, p, v in FATHOM.raw_stats), (194, 0, 1), (335, 0, 5)),
    )
    facts = normalize(item.capture())
    intrinsic, evidence = intrinsic_socket_rolls(facts, ['331:0'])
    assert intrinsic is not None
    assert evidence['331:0'] == {'observed': 35, 'socket': 5, 'intrinsic': 30}
    assert not any('331:0' in gap for gap in roll_gaps(intrinsic, catalog().named['unique', "Death's Fathom"]))
    assert facts.stats['331:0']['value'] == 35
