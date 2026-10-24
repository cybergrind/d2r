"""The Town Portal's held fight (tzloop.py PORTAL_FIGHT_NEAR) and the trip packages folded at the cast
(PORTAL_TRIPS_FOLD), replayed from session 20261024T114646Z-77dea33d (rca/2026-10-24/route-spin-findings.md, "Portal
hold"): the belt-low trip at 15:26:21 held its portal for 8 hostiles within 30 (none within 12) and the level run it
posted fought for 358 s; the room package pushed over it at 15:32:19 went to town and back, and then the belt
package's own portal made a second trip at 15:32:56."""

import logging
import threading
from dataclasses import replace
from types import SimpleNamespace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import merc, tzloop
from inventory_tracking.macros.agenda import RESUME
from inventory_tracking.macros.loop import TOWN, TZ_BACK, TZ_PORTAL, TZ_WAYPOINT
from tests.inventory_tracking.macros.test_tzloop import FETISH, GAME, ROGUE_ENCAMPMENT, Script, at, portals_cast


HELD_RUN = 358.0  # 15:26:21.8 to the cast at 15:32:19.3: the held level run's seconds
LEVEL = 36  # the replay's level (the harness's act 1 trip; the live one was in act 4)


def pack(game: Script) -> None:
    """The pack of 15:26:21: 8 hostiles within 30 of the character, none within 12."""
    here = game.play.world.player
    assert here is not None
    foes = tuple(
        Monster(80 + n, FETISH, 4, here.x + 15.0 + n, here.y + (n % 3), life=128, max_life=128) for n in range(8)
    )
    game.play.world = replace(game.play.world, monsters=foes)


def belt_trip(monkeypatch, *, near: bool, fold: bool) -> tuple[Script, list[float], list[str]]:
    """The belt-low package pushed with the pack near (merc.py `trip`), the held fight a level run whose looks ask
    the agenda's policy (running/legs.py `_agenda_policy` -> `worth_skip`) once a second until it says the run ends,
    or HELD_RUN s (the run's own end, as at 15:32:19), and then ends as the runner's (`Agenda.ran`)."""
    monkeypatch.setattr(tzloop, '_portal_fights', {})
    monkeypatch.setattr(tzloop, '_portal_hold', None)
    monkeypatch.setattr(tzloop, 'PORTAL_FIGHT_NEAR', near)
    monkeypatch.setattr(tzloop, 'PORTAL_TRIPS_FOLD', fold)
    game = Script(LEVEL, monkeypatch)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.loop.agenda.push(*merc.merc_package(LEVEL))
    pack(game)
    fought: list[float] = []
    revived: list[str] = []
    monkeypatch.setattr(merc, 'town_routine', lambda run, trips=None: revived.append('merc routine'))

    def fight_back() -> None:
        hold = tzloop._portal_hold
        assert (hold is not None) == near  # a bound only under the switch
        started = hold.started if hold is not None else 0.0
        seconds = next(
            (s for s in range(1, int(HELD_RUN) + 1) if tzloop.worth_skip(game.loop, LEVEL, started + s)), HELD_RUN
        )
        fought.append(float(seconds))
        game.loop.agenda.ran(LEVEL)  # runner.py `_run_over`

    base = game.hands
    game.hands = lambda visit=None: replace(base(visit), fight_back=fight_back)
    return game, fought, revived


def test_switch_off_the_held_fight_is_the_whole_level_run(monkeypatch):
    game, fought, _ = belt_trip(monkeypatch, near=False, fold=False)

    assert game.leg() == TZ_PORTAL
    assert fought == [HELD_RUN]  # 15:26:21: the portal waited out the level run
    assert portals_cast(game) == []


def test_the_held_fight_ends_after_its_seconds_and_the_portal_is_asked_again(monkeypatch, caplog):
    game, fought, _ = belt_trip(monkeypatch, near=True, fold=False)
    runs = game.loop.agenda.worked[LEVEL]

    with caplog.at_level(logging.INFO, logger=LOG.name):
        legs = [game.leg() for _ in range(tzloop.PORTAL_FIGHTS + 1)]

    assert legs == [TZ_PORTAL] * (tzloop.PORTAL_FIGHTS + 1)
    # Each fight PORTAL_FIGHT_SECONDS, the portal asked again after it; the pack still near: cast all the same
    assert fought == [tzloop.PORTAL_FIGHT_SECONDS] * tzloop.PORTAL_FIGHTS
    assert sum(fought) < HELD_RUN / 10
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]
    assert game.loop.agenda.worked[LEVEL] == runs  # a held fight is no run of its level
    assert caplog.text.count('the held fight is over after 8 s') == tzloop.PORTAL_FIGHTS


def test_a_pack_gone_after_the_held_fight_is_no_reason_to_wait_the_portal_is_cast(monkeypatch):
    game, fought, _ = belt_trip(monkeypatch, near=True, fold=False)

    assert game.leg() == TZ_PORTAL  # held: never cast with the pack on the character
    assert portals_cast(game) == []
    game.play.world = at(LEVEL)  # fought: none within SIGHT
    assert game.leg() == TZ_PORTAL

    assert fought == [tzloop.PORTAL_FIGHT_SECONDS]
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]
    assert tzloop._portal_hold is None


def test_a_held_fight_whose_goal_is_gone_is_not_ended_by_it(monkeypatch):
    game, _, _ = belt_trip(monkeypatch, near=True, fold=False)
    goal = game.loop.agenda.stack[-1]
    hands = replace(game.hands(), fight_back=lambda: None)  # posted, not yet looked at
    assert tzloop.portal_fight(game.play.run(), hands, GAME, goal, game.loop.agenda)
    hold = tzloop._portal_hold
    assert hold is not None
    game.loop.agenda.stack.clear()  # a new game's agenda, a cut package

    assert not tzloop.worth_skip(game.loop, LEVEL, hold.started + 60.0)


def room_trip_over_the_held_one(monkeypatch, *, fold: bool) -> tuple[Script, list[str], list[str]]:
    """15:26:21 held, then 15:32:19: the room package pushed over the belt one (loop: no room for a rare), the pack
    gone; the legs to the run's next goal."""
    game, _, revived = belt_trip(monkeypatch, near=True, fold=fold)
    assert game.leg() == TZ_PORTAL
    game.play.world = at(LEVEL)
    tzloop.trip(game.loop, GAME, LEVEL)
    legs = []
    for _ in range(12):
        legs.append(game.leg(visit=lambda exit: None))
        if all(goal.kind == RESUME for goal in game.loop.agenda.stack):
            break  # the trips made: the run's next goal
    return game, legs, revived


def test_switch_off_the_held_package_makes_a_second_trip_after_the_room_trip(monkeypatch):
    game, legs, revived = room_trip_over_the_held_one(monkeypatch, fold=False)

    trip = [TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_WAYPOINT, TZ_BACK]
    assert legs == [*trip, TZ_PORTAL, TZ_WAYPOINT, TOWN, merc.MERC_TRIP, TZ_WAYPOINT, TZ_BACK]  # 15:32:56: again
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)] * 2
    assert revived == ['merc routine']


def test_the_held_package_is_folded_into_the_trip_cast_over_it(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger=LOG.name):
        game, legs, revived = room_trip_over_the_held_one(monkeypatch, fold=True)

    # One trip: the belt package's revive after the room trip's visit, its portal and way back dropped
    assert legs == [TZ_PORTAL, TZ_WAYPOINT, TOWN, merc.MERC_TRIP, TZ_WAYPOINT, TZ_BACK]
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]
    assert revived == ['merc routine']
    assert all(goal.kind == RESUME for goal in game.loop.agenda.stack)
    assert 'the trip folded in' in caplog.text


def test_a_gheeds_swap_under_the_trip_is_not_folded(monkeypatch):
    from inventory_tracking.macros.agenda import gheeds_package, room_package

    monkeypatch.setattr(tzloop, 'PORTAL_TRIPS_FOLD', True)
    game = Script(LEVEL, monkeypatch)
    agenda = game.loop.agenda
    agenda.begin(game.loop.observe(game.play.world))
    agenda.push(*gheeds_package(LEVEL))
    agenda.push(*room_package(LEVEL))
    before = list(agenda.stack)

    tzloop.fold_trips(agenda, agenda.stack[-1])

    assert agenda.stack == before


def test_the_leg_after_a_held_fight_drops_the_hold_whatever_its_goal(monkeypatch):
    # A queue portal ("for the next part of the zone") may be followed by another goal's run: never ended by the hold
    game, _, _ = belt_trip(monkeypatch, near=True, fold=False)
    goal = game.loop.agenda.stack[-1]
    hands = replace(game.hands(), fight_back=lambda: None)
    assert tzloop.portal_fight(game.play.run(), hands, GAME, goal, game.loop.agenda)
    hold = tzloop._portal_hold
    assert hold is not None
    assert tzloop.worth_skip(game.loop, LEVEL, hold.started + 9.0)  # over: the held run ends
    game.loop.agenda.ran(LEVEL)

    tzloop.portal_hold_done(game.loop.agenda)  # `perform`'s first step, any goal

    assert tzloop._portal_hold is None
    assert not tzloop.worth_skip(game.loop, LEVEL, hold.started + 60.0)
    assert game.loop.agenda.worked[LEVEL] == 0  # taken back


# tzloop.py PORTAL_FIGHT_PLAIN, running/legs.py `_bound_plain`, `_plain_over`: the plain run held on a level no longer
# terrorized (52 s at 22:01:10 on 2026-10-23), which no policy ends


def turned_hold(monkeypatch, *, plain: bool) -> tuple[Script, list[str]]:
    game, _, _ = belt_trip(monkeypatch, near=True, fold=False)
    monkeypatch.setattr(tzloop, 'PORTAL_FIGHT_PLAIN', plain)
    fought: list[str] = []
    hands = replace(game.hands(), fight=lambda: fought.append('plain'), terrorized=lambda area: False)
    goal = game.loop.agenda.stack[-1]
    assert tzloop.portal_fight(game.play.run(), hands, GAME, goal, game.loop.agenda)
    assert fought == ['plain']
    return game, fought


def test_switch_off_the_held_plain_run_has_no_bound(monkeypatch):
    turned_hold(monkeypatch, plain=False)

    assert tzloop._portal_hold is None  # PORTAL_FIGHT_NEAR alone: the agenda run's only
    assert tzloop.plain_fight_bound() is None


def test_the_held_plain_run_gets_the_fights_seconds(monkeypatch):
    turned_hold(monkeypatch, plain=True)

    hold = tzloop._portal_hold
    assert hold is not None
    assert hold.plain
    seconds = tzloop.plain_fight_bound()
    assert seconds is not None
    assert tzloop.PORTAL_FIGHT_SECONDS - 1.0 < seconds <= tzloop.PORTAL_FIGHT_SECONDS


def runner_of(game: Script, pressed_at: float) -> tuple[SimpleNamespace, SimpleNamespace]:
    from inventory_tracking.macros.running.base import ATTACK

    hunter = SimpleNamespace(pursuit=SimpleNamespace(pressed_at=pressed_at))
    runner = SimpleNamespace(
        lock=threading.RLock(), loop=game.loop, attack_mode=True, working=True, routine=ATTACK,
        cancelled=threading.Event(),
    )  # fmt: skip
    return runner, hunter


def test_the_runner_ends_the_held_plain_run_once_its_seconds_are_up(monkeypatch, caplog):
    from inventory_tracking.macros.running import legs

    game, _ = turned_hold(monkeypatch, plain=True)
    hold = tzloop._portal_hold
    assert hold is not None
    timers: list[tuple] = []

    class Timer:
        def __init__(self, seconds, call, args):
            timers.append((seconds, call, args))

        def start(self) -> None:
            pass

    monkeypatch.setattr(legs.threading, 'Timer', Timer)
    runner, hunter = runner_of(game, 7.0)
    legs._bound_plain(runner, hunter, 8.0)  # type: ignore[arg-type]
    assert [(seconds, args[2]) for seconds, _, args in timers] == [(8.0, 7.0)]

    assert not legs._plain_over(runner, hunter, 7.0)  # type: ignore[arg-type]  # its seconds not up yet
    assert runner.attack_mode
    hold.started -= tzloop.PORTAL_FIGHT_SECONDS
    assert not legs._plain_over(runner, hunter, 6.0)  # type: ignore[arg-type]  # another run on now
    with caplog.at_level(logging.INFO, logger=LOG.name):
        assert legs._plain_over(runner, hunter, 7.0)  # type: ignore[arg-type]

    assert not runner.attack_mode
    assert runner.cancelled.is_set()
    assert 'the held fight is over after 8 s' in caplog.text
    # The next leg asks the portal again: none within SIGHT, it is cast
    game.play.world = at(LEVEL)
    assert game.leg() == TZ_PORTAL
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]


def test_with_the_loop_off_or_the_run_over_the_timer_does_nothing(monkeypatch):
    from inventory_tracking.macros.running import legs

    game, _ = turned_hold(monkeypatch, plain=True)
    hold = tzloop._portal_hold
    assert hold is not None
    hold.started -= tzloop.PORTAL_FIGHT_SECONDS
    runner, hunter = runner_of(game, 7.0)
    runner.attack_mode = False  # over by itself
    assert not legs._plain_over(runner, hunter, 7.0)  # type: ignore[arg-type]
    runner.attack_mode, game.loop.on = True, False  # the player's KP_6 off
    assert not legs._plain_over(runner, hunter, 7.0)  # type: ignore[arg-type]
    assert not runner.cancelled.is_set()
