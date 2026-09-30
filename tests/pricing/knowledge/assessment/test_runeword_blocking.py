"""Runeword shield market bonuses exclude native blocking and retain rune effects."""

from dataclasses import replace

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem
from tests.pricing.knowledge.assessment.test_comparables import listing


def rhyme():
    # Bone Shield base20 + Rhyme20. Shael grants 20FBR in addition to recipe20.
    return Item(
        'Bone Shield',
        'normal',
        'Rhyme',
        (
            (20, 0, 40),
            (31, 0, 25),
            (102, 0, 40),
            (27, 0, 15),
            (153, 0, 1),
            (80, 0, 25),
            (79, 0, 50),
            *((sid, 0, 25) for sid in (39, 41, 43, 45)),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled',
        runeword='Rhyme',
        complete=True,
        socket_items=(SocketItem('Shael Rune'), SocketItem('Eth Rune')),
    )


def test_rhyme_market_contract_compares_bonus_not_native_total():
    facts = normalize(rhyme().capture())
    contract, gaps = RunewordHandler().contract(facts, 'shield')
    assert not gaps
    assert contract.properties['446'] == contract.intrinsic_properties['446'] == 20
    assert facts.stats['20:0']['value'] == 40
    common = {
        'name': 'Rhyme',
        'rarity': 'runeword',
        'sockets': 2,
        'socket_contents': 'filled',
        'base_code': facts.base_code,
        'base_rarity': 'normal',
    }
    values = dict(contract.properties)
    rows = [
        listing('bonus', **common, properties={**values, '446': 20}),
        listing('total', **common, properties={**values, '446': 40}),
    ]
    comparisons = evaluate(contract.to_dict(), rows)
    assert [row['listing_id'] for row in comparisons['accepted']] == ['bonus']
    assert [row['listing_id'] for row in comparisons['rejected']] == ['total']


def test_runeword_missing_native_blocking_cannot_borrow_base_default():
    item = rhyme()
    facts = normalize(replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 20)).capture())
    contract, gaps = RunewordHandler().contract(facts, 'shield')
    assert contract is None
    assert any('blocking' in gap.lower() for gap in gaps)
