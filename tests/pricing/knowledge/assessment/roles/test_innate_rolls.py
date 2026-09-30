"""Socket bonuses cannot turn an ordinary named-item roll into a perfect one."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem


RULE = {'op': 'innate_stat_at_least', 'key': '358:0', 'value': 8}


def helmet(total, jewel=10):
    from inventory_tracking.items.metadata import metadata

    base = next(b['name'] for b in metadata()['bases'].values() if b['code'] == 'cjw')
    child = SocketItem(base, ((358, 0, jewel),), name="Guardian's Light", complete=True)
    return Item(
        'Death Mask',
        'unique',
        "Hellwarden's Will",
        ((358, 0, total), (194, 0, 1)),
        sockets=1,
        socket_contents='filled',
        socket_items=(child,),
    )


@pytest.mark.parametrize(
    ('native', 'jewel', 'truth'), [(5, 10, 'false'), (8, 10, 'true'), (8, 5, 'true'), (7, 5, 'false')]
)
def test_preference_uses_helmet_roll_after_known_jewel_contribution(native, jewel, truth):
    result = evaluate(RULE, normalize(helmet(native + jewel, jewel).capture()))
    assert result.truth == truth
    assert result.observed == native


@pytest.mark.parametrize(
    'change', ['unread_jewel', 'missing_child', 'unknown_sockets', 'impossible_roll', 'duplicate_child']
)
def test_uncertain_or_conflicting_socket_evidence_cannot_prove_perfection(change):
    item = helmet(18)
    if change == 'unread_jewel':
        item = replace(item, socket_items=(replace(item.socket_items[0], raw_stats=(), complete=False),))
    elif change == 'missing_child':
        item = replace(item, socket_items=(), socket_contents='unknown')
    elif change == 'unknown_sockets':
        item = replace(item, sockets=None, raw_stats=((358, 0, 18),), socket_contents='unknown')
    elif change == 'impossible_roll':
        item = helmet(20)
    capture = item.capture()
    if change == 'duplicate_child':
        capture['item']['socket_items'] *= 2
    assert evaluate(RULE, normalize(capture)).truth == 'unknown'


def test_empty_socket_and_wrong_predicate_key():
    item = Item('Death Mask', 'unique', "Hellwarden's Will", ((358, 0, 8),))
    assert evaluate(RULE, normalize(item.capture())).truth == 'true'
    with pytest.raises(ValueError, match='innate'):
        validate({**RULE, 'key': '16:0'})  # Percent defense is not this additive rule.
