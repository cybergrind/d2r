"""The loop's stop rules (macros/stops.py): a row per rule in its order, and every combination of the facts against the
if-chain runner.py `_loop_stopped` was until 2026-10-19 (kept below as the spec)."""

import itertools
from typing import get_args

import pytest

from inventory_tracking.macros.actuator import Cause
from inventory_tracking.macros.stops import ROOM_CAUSES, Beset, Remedy, Stopped, decide, first, low_life


CAUSES: tuple[Cause, ...] = get_args(Cause)
R = Remedy


@pytest.mark.parametrize(
    ('cause', 'on', 'dead', 'expected'),
    [
        ('room', True, True, R.DEAD),  # dead first, whatever the cause
        ('other', False, True, R.DEAD),  # the loop off too
        ('beset', True, False, R.LEAVE),  # no facts read: left as before
        ('hand', True, False, R.AGAIN),
        ('stash', True, False, R.STOP),
        ('idle', True, False, R.STOP),  # nothing to play (macros/tzloop.py `choose`): no game churn
        ('zone', True, False, R.LEAVE),  # a zone not playable: left, the next one waited for in the lobby
        ('zone', False, False, None),
        ('lobby', True, False, R.LEAVE),  # a game creation failed once: tried again
        ('lobby', False, False, None),
        ('idle', False, False, None),
        ('beset', False, False, None),  # off: nothing by the cause
        ('hand', False, False, None),
        ('room', True, False, None),
        ('stall', True, False, None),
        ('refused', True, False, None),
        ('other', True, False, None),
    ],
)
def test_the_rules_by_the_cause_alone_come_before_the_swap(cause, on, dead, expected):
    assert first(cause, on=on, dead=dead) is expected


def test_a_second_game_creation_failed_in_a_row_stops_the_loop():
    # 05:35:30 on 2026-10-20: Battle.net dropped the client to the character screen (the Offline tab); the lobby's
    # clicks and keys went there for 5 min, 9 tries
    from inventory_tracking.macros.stops import LOBBY_STOPS

    assert first('lobby', on=True, dead=False, lobby_fails=LOBBY_STOPS - 1) is R.LEAVE
    assert first('lobby', on=True, dead=False, lobby_fails=LOBBY_STOPS) is R.STOP
    assert first('lobby', on=True, dead=True, lobby_fails=LOBBY_STOPS) is R.DEAD


@pytest.mark.parametrize(
    ('beset', 'on', 'dead', 'expected'),
    [
        # The player, 2026-10-19: "Fight back first: fight the attacker, then pick up the valuable; leave only if life
        # gets low (the death rules still win)"
        (Beset(low=False, foe=True, left='Flawless Topaz'), True, False, R.FIGHT),
        (Beset(low=False, foe=True), True, False, R.FIGHT),  # nothing on the ground: fought back all the same
        (Beset(low=False, left='Flawless Topaz'), True, False, R.FIGHT),  # no attacker read, a valuable kept
        (Beset(low=False), True, False, R.LEAVE),  # no attacker read, nothing to keep: left as before
        (Beset(low=True, foe=True, left='Flawless Topaz'), True, False, R.LEAVE),  # life low: left, valuable or not
        (Beset(low=False, again=True, foe=True, left='Ring'), True, False, R.LEAVE),  # the fight back lost
        (Beset(low=False, foe=True, left='Ring'), True, True, R.DEAD),  # dead: nothing at all
        (Beset(low=False, foe=True, left='Ring'), False, False, None),  # the player's KP_6 pause
    ],
)
def test_a_beset_stop_is_fought_back_unless_life_is_low_or_the_fight_back_lost(beset, on, dead, expected):
    assert first('beset', on=on, dead=dead, beset=beset) is expected


def test_life_is_low_under_the_healers_floor():
    from inventory_tracking.config import HEAL_PRIORITY

    assert HEAL_PRIORITY.floor == 65.0
    assert not low_life((2789, 3134))  # 89 %: the near-death take's first beset (2026-10-19 09:36:57)
    assert not low_life((2038, 3134))
    assert low_life((2036, 3134))
    assert low_life(None)  # unread
    assert low_life((0, 0))


ON = {'on': True, 'game': 'cyber1'}


@pytest.mark.parametrize(
    ('stop', 'expected'),
    [
        (Stopped('other', **ON), R.RECOVER),  # nothing on the ground: leave the game, go on
        (Stopped('other', on=False), R.NOTHING),
        (Stopped('other', **ON, left='Ring'), R.FETCH),  # not room: the leg again, once a game
        (Stopped('other', **ON, left='Ring', fetched=True), R.CUBE),
        (Stopped('other', **ON, left='Ring', fetched=True, cubed=True, trips=True), R.HOLD),  # no trip but for room
        (Stopped('room', **ON, left='Ring'), R.CUBE),  # room: the cube first
        (Stopped('stall', **ON, left='Ring'), R.CUBE),  # the stand counts as room (ruling pending)
        (Stopped('room', **ON, left='Ring', cubed=True, packaged=True, trips=True), R.PACKAGE),
        (Stopped('room', **ON, left='Ring', cubed=True, trips=True), R.TRIP),
        (Stopped('room', **ON, left='Ring', cubed=True), R.DROP),
        (Stopped('room', **ON, left='Ring', cubed=True, dropped=True), R.HOLD),  # never a game left with it
        (Stopped('room', True, 'Ring', None), R.HOLD),  # no game read: no once-a-game rule
        (Stopped('refused', **ON, left='Unique Grand Charm'), R.FETCH),
    ],
)
def test_each_rule_after_the_swap_in_its_order(stop, expected):
    assert decide(stop) is expected


def spec(stop: Stopped) -> Remedy:
    """runner.py `_loop_stopped` after the Gheed's swap, as it was before the rules moved to macros/stops.py."""
    roomy = stop.cause in ROOM_CAUSES
    left, game = stop.left, stop.game
    if left is not None and not roomy and not stop.fetched:
        return R.FETCH
    if left is not None and game is not None and not stop.cubed:
        return R.CUBE
    if roomy and left is not None and game is not None and stop.packaged:
        return R.PACKAGE
    if roomy and left is not None and game is not None and stop.trips:
        return R.TRIP
    if roomy and left is not None and game is not None and not stop.dropped:
        return R.DROP
    if left is not None:
        return R.HOLD
    return R.RECOVER if stop.on else R.NOTHING


def test_every_combination_of_the_facts_is_answered_as_before():
    flags = (False, True)
    seen = set()
    for cause, on, left, game, *marks in itertools.product(
        CAUSES, flags, (None, 'Ring'), (None, 'cyber1'), flags, flags, flags, flags, flags
    ):
        stop = Stopped(cause, on, left if on else None, game, *marks)
        assert decide(stop) is spec(stop), stop
        seen.add(decide(stop))
    assert seen == set(Remedy) - {R.DEAD, R.LEAVE, R.FIGHT, R.AGAIN, R.STOP}
