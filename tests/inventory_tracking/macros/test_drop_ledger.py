"""The level run's drop ledger (macros/drop_ledger.py): tries, why given up, once-said sets, forgetting."""

from inventory_tracking.macros.drop_ledger import GATHER_TRIES, SAID_MOST, DropLedger


def test_a_drop_is_spent_after_its_tries_and_says_what_the_last_came_to():
    ledger = DropLedger()
    ledger.gathered[7] = GATHER_TRIES - 1
    assert not ledger.spent(7)
    ledger.gathered[7] = GATHER_TRIES
    assert ledger.spent(7)
    assert ledger.given_up(7) == f'given up after {GATHER_TRIES} tries: still on the ground after each'
    ledger.tried[7] = 'priced act expired'
    assert ledger.given_up(7) == f'given up after {GATHER_TRIES} tries (the last: priced act expired)'


def test_a_unit_is_first_once_and_a_full_set_starts_afresh():
    ledger = DropLedger()
    assert ledger.first(ledger.left_said, 1)
    assert not ledger.first(ledger.left_said, 1)
    ledger.left_said.update(range(100, 100 + SAID_MOST + 1))
    assert ledger.first(ledger.left_said, 2)
    assert ledger.left_said == {2}


def test_forget_clears_every_memory():
    ledger = DropLedger({1: 2}, {1: 'x'}, {1}, {1}, {1})
    ledger.forget()
    assert ledger == DropLedger()
