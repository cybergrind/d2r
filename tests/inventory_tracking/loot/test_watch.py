"""Rune watcher: arrow rows for valuable ground runes, published while any are in range."""

import logging
import threading

from inventory_tracking.levels.model import Location
from inventory_tracking.loot.ground import GroundRune, Shrine
from inventory_tracking.loot.watch import RuneWatcher


class Source:
    pid, images, capture = 7, {}, {}

    def ensure_connected(self):
        pass


def watcher(found, *, lock=None, focused=True):
    shown = []
    watch = RuneWatcher(
        Source(),
        capture_lock=lock or threading.Lock(),
        focused=lambda images: focused,
        display=shown.append,
        poll_interval=0.5,
        minimum='r21',
        observe=lambda pid, images, capture, *, minimum, shrine_types, super_chests: found(),
        shrine_types=frozenset({18}),
    )
    return watch, shown


PLAYER = Location(74, 0, 25450, 5442)


def test_valuable_runes_become_arrow_rows_highest_first():
    runes = [GroundRune(645, 1, 25450, 5300), GroundRune(654, 2, 25600, 5442)]
    watch, shown = watcher(lambda: (PLAYER, runes, []))

    watch.poll(1.0)
    watch.tick()

    assert [line.text for line in shown[-1]] == ['↘  Ber Rune: east', '↗  Pul Rune: north']
    assert all(line.arrow for line in shown[-1])


def test_nothing_in_range_clears_the_card():
    found = {'runes': [GroundRune(654, 2, 25600, 5442)]}
    watch, shown = watcher(lambda: (PLAYER, found['runes'], []))
    watch.poll(1.0)
    watch.tick()
    found['runes'] = []

    watch.poll(2.0)
    watch.tick()

    assert shown[-1] == []


def test_new_runes_are_logged_once(caplog):
    watch, _ = watcher(lambda: (PLAYER, [GroundRune(654, 2, 25600, 5442)], []))

    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        watch.poll(1.0)
        watch.poll(2.0)

    assert [r.getMessage() for r in caplog.records if 'Ber Rune' in r.getMessage()] == [
        'Ground rune: Ber Rune at (25600, 5442)'
    ]


def test_busy_lock_or_unfocused_game_shows_nothing():
    lock = threading.Lock()
    watch, shown = watcher(lambda: (PLAYER, [GroundRune(654, 2, 25600, 5442)], []), lock=lock)
    with lock:
        watch.poll(1.0)
    watch.tick()
    assert shown in ([], [[]])

    unfocused, shown = watcher(lambda: (PLAYER, [GroundRune(654, 2, 25600, 5442)], []), focused=False)
    unfocused.poll(1.0)
    unfocused.tick()
    assert all(frame == [] for frame in shown)


def test_gem_shrines_are_listed_before_runes():
    watch, shown = watcher(lambda: (PLAYER, [GroundRune(645, 1, 25450, 5300)], [Shrine(18, 9, 25300, 5442)]))

    watch.poll(1.0)
    watch.tick()

    assert [line.text for line in shown[-1]] == ['↖  Gem Shrine: west', '↗  Pul Rune: north']


def test_loot_rows_are_pois():
    from inventory_tracking.presentation import Tone

    watch, shown = watcher(lambda: (PLAYER, [GroundRune(645, 1, 25450, 5300)], [Shrine(18, 9, 25300, 5442)]))

    watch.poll(1.0)
    watch.tick()

    assert {line.tone for line in shown[-1]} == {Tone.POI}


def test_super_chests_are_listed_with_the_shrines_before_runes():
    from inventory_tracking.loot.ground import SuperChest

    watch, shown = watcher(lambda: (PLAYER, [GroundRune(645, 1, 25450, 5300)], [SuperChest(9, 25300, 5442)]))

    watch.poll(1.0)
    watch.tick()

    assert [line.text for line in shown[-1]] == ['↖  Super chest: west', '↗  Pul Rune: north']
