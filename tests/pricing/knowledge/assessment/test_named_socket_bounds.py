from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


HEAVEN = Item(
    'Mighty Scepter',
    'unique',
    "Heaven's Light",
    (
        (17, 0, 300),
        (18, 0, 300),
        (93, 0, 20),
        (116, 0, 33),
        (89, 0, 3),
        (139, 0, 20),
        (136, 0, 33),
        (194, 0, 2),
        (83, 3, 3),
    ),
    sockets=2,
    complete=True,
)


@pytest.mark.parametrize(('count', 'valid'), [(0, False), (1, True), (2, True), (3, False)])
def test_heavens_light_native_roll_is_capped_by_original_base(count, valid):
    item = replace(
        HEAVEN, sockets=count, raw_stats=tuple((s, p, count if s == 194 else v) for s, p, v in HEAVEN.raw_stats)
    )
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
    assert (contract is not None) is valid, gaps


@pytest.mark.parametrize(('count', 'valid'), [(0, False), (1, False), (2, True), (3, False)])
def test_parameter_only_socket_property_is_required(count, valid):
    from pricing.knowledge.assessment.mechanics.named_sockets import socket_gaps
    from pricing.knowledge.definition_store import catalog

    item = Item('Tulwar', 'unique', 'Blade of Ali Baba', ((194, 0, count),), sockets=count, complete=True)
    assert (not socket_gaps(normalize(item.capture()), catalog().named['unique', item.name])) is valid


@pytest.mark.parametrize(('count', 'valid'), [(1, False), (2, True), (3, True), (4, False), (5, False)])
def test_upgraded_aldur_retains_original_socket_outcomes(count, valid):
    from pricing.knowledge.assessment.mechanics.named_sockets import socket_gaps
    from pricing.knowledge.definition_store import catalog
    from pricing.knowledge.market_base_catalog import equipment_base

    original = Item('Jagged Star', 'set', "Aldur's Rhythm", ((194, 0, count),), sockets=count, complete=True)
    facts = normalize(original.capture())
    # Upgrading preserves sockets; a larger elite cap cannot reroll the item.
    for base in ('Jagged Star', 'Devil Star'):
        changed = replace(facts, base_name=base, base_code=equipment_base(base)[0]['base_code'])
        assert (not socket_gaps(changed, catalog().named['set', original.name])) is valid


@pytest.mark.parametrize('change', [{'sockets': 1}, {'stats': {}}, {'item_level': 25}])
def test_socket_evidence_and_item_level_are_checked(change):
    from pricing.knowledge.assessment.mechanics.named_sockets import socket_gaps
    from pricing.knowledge.definition_store import catalog

    item = Item('Cryptic Axe', 'unique', 'Tomb Reaver', ((194, 0, 3),), sockets=3, complete=True)
    facts = normalize(item.capture())
    # Polearms cap at three even in the lowest band; legal evidence stays legal.
    gaps = socket_gaps(replace(facts, **change), catalog().named['unique', item.name])
    assert bool(gaps) is ('item_level' not in change)


def test_known_socket_filler_preserves_native_socket_validation():
    from tests.pricing.knowledge.assessment.item_bank.models import SocketItem

    item = replace(
        HEAVEN,
        sockets=1,
        socket_contents='filled',
        socket_items=(SocketItem('Shael Rune', complete=True),),
        raw_stats=tuple((s, p, 40 if s == 93 else 1 if s == 194 else v) for s, p, v in HEAVEN.raw_stats),
    )
    contract, gaps = NamedHandler().contract(normalize(item.capture()), 'weapon')
    assert contract is not None, gaps
