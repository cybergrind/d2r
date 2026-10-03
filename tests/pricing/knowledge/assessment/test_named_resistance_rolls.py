from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem


def kira(resistances, *, rune=None):
    return Item(
        'Tiara',
        'unique',
        "Kira's Guardian",
        ((31, 0, 100), (99, 0, 20), (153, 0, 1), *zip((39, 41, 43, 45), (0,) * 4, resistances, strict=True)),
        complete=True,
        sockets=1 if rune else 0,
        socket_contents='filled' if rune else 'empty',
        socket_items=(SocketItem(rune, (), complete=True),) if rune else (),
    )


@pytest.mark.parametrize(
    ('res', 'valid'),
    [((50,) * 4, True), ((70,) * 4, True), ((49,) * 4, False), ((71,) * 4, False), ((60, 61, 60, 60), False)],
)
def test_kira_requires_one_legal_all_resistance_roll(res, valid):
    contract, gaps = NamedHandler().contract(normalize(kira(res).capture()), 'helm')
    assert (contract is not None) is valid, gaps


@pytest.mark.parametrize(
    ('res', 'valid'), [((100, 70, 70, 70), True), ((100, 69, 70, 70), False), ((101, 71, 71, 71), False)]
)
def test_kira_ral_is_removed_before_shared_roll_check(res, valid):
    contract, gaps = NamedHandler().contract(normalize(kira(res, rune='Ral Rune').capture()), 'helm')
    assert (contract is not None) is valid, gaps
    if valid:
        assert contract.socket_payload == ('Ral Rune',)


def test_independent_resistance_rolls_need_not_be_equal():
    from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps

    item = Item('Mesh Boots', 'set', "Natalya's Soul", ((41, 0, 15), (43, 0, 25)), complete=True)
    facts = normalize(item.capture())
    definition = catalog().named['set', "Natalya's Soul"]
    gaps = roll_gaps(facts, definition)
    assert not any('shared roll' in g or ' 41:0 ' in g or ' 43:0 ' in g for g in gaps)
    for stat in (41, 43):
        altered = replace(facts, stats={**facts.stats, f'{stat}:0': {'status': 'decoded', 'value': 26}})
        assert any(f' {stat}:0 ' in g for g in roll_gaps(altered, definition))


def test_named_all_attributes_are_one_roll_too():
    from pricing.knowledge.assessment.mechanics.named_rolls import roll_gaps

    facts = normalize(kira((60,) * 4).capture())
    definition = catalog().named['unique', 'Azurewrath']
    for values, valid in (((10,) * 4, True), ((5,) * 4, True), ((5, 6, 5, 5), False)):
        stats = {f'{s}:0': {'status': 'decoded', 'value': v} for s, v in enumerate(values)}
        gaps = roll_gaps(replace(facts, stats=stats), definition)
        assert (not any('all-stats' in gap for gap in gaps)) is valid
