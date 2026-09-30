"""Stash watcher: one collection per open → closed edge, nothing on noise or gaps."""

from inventory_tracking.collection.watch import StashWatcher
from inventory_tracking.models import Observation


def observed(stash):
    return Observation(0.0, {'stash': stash, 'inventory': stash})


def make(sequence, *, accept=True):
    reads = iter(sequence)
    requested = []

    def collect(now):
        requested.append(now)
        return accept

    watcher = StashWatcher(lambda: next(reads), collect, poll_interval=0.5)
    return watcher, requested


def test_collects_once_when_the_stash_closes():
    watcher, requested = make([observed(False), observed(True), observed(True), observed(False), observed(False)])
    assert [watcher.poll(t) for t in (0.0, 0.5, 1.0, 1.5, 2.0)] == [False, False, False, True, False]
    assert requested == [1.5]
    assert watcher.collections == 1


def test_closed_from_the_start_and_reopen_without_close_do_nothing():
    watcher, requested = make([observed(False), observed(False), observed(True), observed(True)])
    assert not any(watcher.poll(t) for t in (0.0, 0.5, 1.0, 1.5))
    assert requested == []


def test_unreadable_flags_forget_the_open_state():
    watcher, requested = make([observed(True), Observation.unavailable(0.0, 'gone'), observed(False)])
    assert [watcher.poll(t) for t in (0.0, 0.5, 1.0)] == [False, False, False]
    assert requested == []
    assert watcher.stash_open is False


def test_polls_no_faster_than_the_interval_and_counts_only_accepted_requests():
    watcher, requested = make([observed(True), observed(False), observed(True), observed(False)], accept=False)
    assert not watcher.poll(0.0)
    assert not watcher.poll(0.2)  # too soon: no read consumed
    assert not watcher.poll(0.5)  # closed: requested but refused
    assert requested == [0.5]
    assert watcher.collections == 0
