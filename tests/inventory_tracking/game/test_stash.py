"""The stash's one record (inventory_tracking/game/stash.py)."""

import json
from types import SimpleNamespace

from inventory_tracking.game.records import Page, StashView
from inventory_tracking.game.stash import SNAPSHOT_SECONDS, STACK_MOST, Stash, full_of, read_snapshot
from inventory_tracking.items.grid import STASH_SIZE, Grid


EASTERN, ESSENCE, REJUVENATION = 675, 669, 610  # Eastern Worldstone Shard, Twisted Essence, a potion class


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def view(**stacks: int) -> StashView:
    classes = {'eastern': EASTERN, 'essence': ESSENCE, 'rejuvenation': REJUVENATION}
    return StashView((Page(0, Grid.empty(STASH_SIZE)),), tuple(sorted((classes[k], n) for k, n in stacks.items())))


def test_unknown_until_read_and_unknown_means_nothing_is_full():
    stash = Stash()
    assert stash.current() is None
    assert stash.full() == frozenset()
    assert stash.count(EASTERN) is None
    assert stash.read() is None  # no reader: unread, nothing recorded


def test_a_read_is_recorded_and_a_touch_makes_it_unknown_until_the_next_read():
    # 08:59:26 on 2026-10-22: the full stacks were a file's from 23:24 the night before; the record is the read's
    clock, held = Clock(), [view(eastern=STACK_MOST, essence=STACK_MOST)]
    stash = Stash(lambda: held[0], clock=clock)
    assert stash.read() == held[0]
    assert stash.full() == frozenset({EASTERN, ESSENCE})
    clock.now += 1
    stash.touched()  # the stash panel opened: what is in it may change
    assert stash.current() is None
    assert stash.full() == frozenset()
    held[0] = view(eastern=97, essence=STACK_MOST)  # a shard used by hand
    clock.now += 1
    assert stash.fresh() == held[0]
    assert stash.full() == frozenset({ESSENCE})
    assert stash.count(EASTERN) == 97


def test_an_unread_moment_keeps_the_record():
    held: list[StashView | None] = [view(eastern=90)]
    stash = Stash(lambda: held[0])
    stash.read()
    held[0] = None
    assert stash.read() is None
    assert stash.count(EASTERN) == 90


def test_full_leaves_the_potions_out():
    assert full_of(view(rejuvenation=STACK_MOST, essence=STACK_MOST)) == frozenset({ESSENCE})
    assert full_of(None) == frozenset()


def test_the_snapshot_is_written_at_a_change_and_kept_fresh(tmp_path):
    clock, held = Clock(), [view(eastern=STACK_MOST)]
    path = tmp_path / 'stash.json'
    stash = Stash(lambda: held[0], snapshot=path, clock=clock)
    stash.read(game='cyberr3')
    found = read_snapshot(path)
    assert found is not None
    assert found['full_names'] == ['Eastern Worldstone Shard']
    assert found['game'] == 'cyberr3'
    assert found['stacks'] == {str(EASTERN): STACK_MOST}
    assert found['pages_free'] == {'0': STASH_SIZE[0] * STASH_SIZE[1]}
    path.write_text('{}')  # unchanged and recent: not written again
    clock.now += 1
    stash.read()
    assert json.loads(path.read_text()) == {}
    clock.now += SNAPSHOT_SECONDS
    stash.read()
    assert read_snapshot(path)['full'] == [EASTERN]  # pyrefly: ignore[unsupported-operation]
    held[0] = view(eastern=97)
    clock.now += 1
    stash.read()
    assert read_snapshot(path)['full'] == []  # pyrefly: ignore[unsupported-operation]


def test_the_poll_refreshes_the_record_in_town_and_elsewhere_only_while_unknown():
    from inventory_tracking.macros.running import watch
    from inventory_tracking.native.layout import TOWN_IDS

    clock, reads = Clock(), []

    def read_stash() -> StashView:
        reads.append(clock.now)
        return view(eastern=97)

    runner = SimpleNamespace(loop=SimpleNamespace(stash=Stash(clock=clock)), stash_polled=float('-inf'))
    memory = SimpleNamespace(read_stash=read_stash)
    town, field = min(TOWN_IDS), 37
    watch._stash_poll(runner, memory, 'g1', field)  # pyrefly: ignore[bad-argument-type] the fake runner
    assert reads == [100.0]  # a service start in the field: unknown, tried
    clock.now += watch.REFRESH_SECONDS
    watch._stash_poll(runner, memory, 'g1', field)  # pyrefly: ignore[bad-argument-type]
    assert len(reads) == 1  # known: not read in the field
    watch._stash_poll(runner, memory, 'g1', town)  # pyrefly: ignore[bad-argument-type]
    assert len(reads) == 2  # in town every REFRESH_SECONDS
    clock.now += watch.REFRESH_SECONDS / 2
    watch._stash_poll(runner, memory, 'g1', town)  # pyrefly: ignore[bad-argument-type]
    assert len(reads) == 2
    clock.now += watch.REFRESH_SECONDS
    watch._stash_poll(runner, memory, None, town)  # pyrefly: ignore[bad-argument-type] the lobby
    assert len(reads) == 2
    watch._stash_poll(runner, memory, 'g2', town)  # pyrefly: ignore[bad-argument-type]
    assert len(reads) == 3
    assert runner.loop.stash.game == 'g2'
