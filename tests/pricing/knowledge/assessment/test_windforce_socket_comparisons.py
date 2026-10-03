from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.cases.late_unique_weapons import WIND
from tests.pricing.knowledge.assessment.item_bank.models import SocketItem


def windforce(insert, leech, life=0):
    stats = tuple((s, p, leech if s == 62 else v) for s, p, v in WIND.item.raw_stats)
    stats += ((0, 0, 10), (2, 0, 5), (28, 0, 30))
    if life:
        stats += ((60, 0, life),)
    return replace(
        WIND.item,
        complete=True,
        raw_stats=stats,
        sockets=1,
        socket_contents='filled',
        socket_items=(SocketItem(insert),),
    )


@pytest.mark.parametrize(('insert', 'bonus', 'life'), [('Vex Rune', 7, 0), ('Perfect Skull', 3, 4)])
@pytest.mark.parametrize('native', [6, 7, 8])
def test_named_comparison_retains_total_leech_and_exact_socket_identity(insert, bonus, life, native):
    facts = normalize(windforce(insert, native + bonus, life).capture())
    contract, gaps = NamedHandler().contract(facts, 'weapon')
    assert not gaps
    assert contract.properties['463'] == native + bonus
    assert contract.socket_payload == (insert,)
    assert facts.stats['62:0']['value'] == native + bonus


@pytest.mark.parametrize('native', [5, 9])
def test_socket_bonus_cannot_hide_illegal_native_roll(native):
    contract, gaps = NamedHandler().contract(normalize(windforce('Vex Rune', native + 7).capture()), 'weapon')
    assert contract is None
    assert gaps


def test_missing_payload_is_not_assumed_to_be_vex_from_total_leech():
    item = replace(windforce('Vex Rune', 15), socket_items=())
    assert NamedHandler().contract(normalize(item.capture()), 'weapon')[0] is None


@pytest.mark.parametrize(
    ('insert', 'bonus', 'life'),
    [
        ('Amn Rune', 0, 7),
        ('Chipped Skull', 1, 2),
        ('Flawed Skull', 2, 2),
        ('Skull', 2, 3),
        ('Flawless Skull', 3, 3),
    ],
)
def test_native_leech_fillers_keep_both_effects_in_comparison(insert, bonus, life):
    contract, gaps = NamedHandler().contract(normalize(windforce(insert, 7 + bonus, life).capture()), 'weapon')
    assert not gaps
    assert contract.properties['463'] == 7 + bonus
    assert contract.properties['462'] == life
    assert contract.socket_payload == (insert,)


def test_vex_listing_cannot_compare_as_empty_or_as_another_insert():
    from pricing.knowledge.assessment.comparables import reject_reasons

    contract, gaps = NamedHandler().contract(normalize(windforce('Vex Rune', 15).capture()), 'weapon')
    assert not gaps
    request = contract.to_dict()
    row = {
        **request,
        'properties': {**request['properties'], '934': 'Vex Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'amount': 1,
        'seller_id': 'seller',
        'ask_ist': 1,
    }
    assert not reject_reasons(request, row)
    other = {**row, 'properties': {**row['properties'], '934': 'Perfect Skull'}}
    assert 'Different or unverified socket filler identity.' in reject_reasons(request, other)
    empty = {
        **row,
        'socket_contents': 'empty',
        'properties': {k: v for k, v in row['properties'].items() if k != '934'},
    }
    assert reject_reasons(request, empty)
