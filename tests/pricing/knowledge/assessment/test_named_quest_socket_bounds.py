from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_sockets import socket_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import Item


GAZE = Item(
    'Grim Helm',
    'unique',
    'Vampire Gaze',
    (
        (60, 0, 8),
        (62, 0, 8),
        (36, 0, 20),
        (35, 0, 15),
        (154, 0, 15),
        (16, 0, 100),
        (54, 0, 6),
        (55, 0, 22),
        (56, 0, 100),
        (31, 0, 252),
    ),
    complete=True,
)


@pytest.mark.parametrize('count', [0, 1, 2, 3])
def test_named_without_native_sockets_cannot_gain_multiple_quest_sockets(monkeypatch, count):
    monkeypatch.setattr('pricing.knowledge.assessment.handlers.named.socket_gaps', socket_gaps)
    raw = GAZE.raw_stats + (((194, 0, count),) if count else ())
    facts = normalize(replace(GAZE, sockets=count, raw_stats=raw).capture())
    contract, gaps = NamedHandler().contract(facts, 'helm')
    assert (contract is not None) is (count <= 1), gaps
    if count > 1:
        assert any('socket' in gap.lower() for gap in gaps)


def test_intrinsic_multiple_sockets_keep_their_own_native_rule():
    item = Item('Corona', 'unique', 'Crown of Ages', ((194, 0, 2),), sockets=2, complete=True)
    assert socket_gaps(normalize(item.capture()), catalog().named['unique', 'Crown of Ages']) == []
