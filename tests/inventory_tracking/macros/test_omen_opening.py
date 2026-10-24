"""The quiet before a Herald's pack (macros/hunt.py `omen_open`, OMEN_STRIKE; builds/warlock/buffs.py OMEN_SIGIL's
'opening' row) and the before-strike rows before the press (AHEAD_BEFORE_PRESS), 2026-10-23. The player, ~20:45: "in
herald fight we can put it on pack spawn point BEFORE actual pack spawns, so when it spawns - it already debuffed /
2. we can start striking with echoing strike before actual pack spawns" (rca/2026-10-23/omen-opening-findings.md)."""

import math

import pytest

from inventory_tracking.builds.warlock import buffs as plan
from inventory_tracking.macros import hunt as hunt_module
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.hunt import OMEN_GRACE, OMEN_LEAD, OMEN_SPAWN
from inventory_tracking.macros.hunting.base import HERALD_OMEN, OMEN_SECONDS
from tests.inventory_tracking.macros.test_hunt import CHAMPION, appear, foe, game, hunter, keys, me


MINION = 0x10
SPOTS = ((0.0, 0.0), (1.0, 2.0), (-1.0, -2.0), (2.0, -1.0))


class Logged(list):
    """A fake game's record list that also notes, in `order`, which record each append was."""

    def __init__(self, name: str, order: list[str]) -> None:
        super().__init__()
        self.name, self.order = name, order

    def append(self, item) -> None:
        self.order.append(self.name)
        super().append(item)


def played(monkeypatch, *, strike: bool = False, sigil: bool = False, away: float = 20.0, until: float = 8.0):
    """Attack mode alone (no level run) with an omen `away` east read at the start, its pack of four tier 5 members
    OMEN_SPAWN s on: the game, the spot, the spawn's clock and the order of the sigils and strikes, with what each
    record held when the window opened (OMEN_LEAD before the spawn) and at the spawn."""
    monkeypatch.setattr(hunt_module, 'OMEN_READ_ALONE', True)
    monkeypatch.setattr(hunt_module, 'OMEN_STRIKE', strike)
    monkeypatch.setattr(plan, 'OMEN_SIGIL', sigil)
    play = game()
    hunt = hunter(play)
    order: list[str] = []
    play.sigils, play.strikes = Logged('sigil', order), Logged('strike', order)
    here = (me(play.world).x, me(play.world).y)
    spot = (here[0] + away, here[1])
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    start = play.clock.now
    spawn = start + OMEN_SPAWN
    run.flights = lambda kinds: ((0, HERALD_OMEN, *spot),) if HERALD_OMEN in kinds and play.clock.now < spawn else ()
    pack = [
        foe(20 + k, spot[0] + dx, spot[1] + dy, flags=MINION, tier=5, life=500, max_life=500)
        for k, (dx, dy) in enumerate(SPOTS)
    ]
    seen: dict[str, tuple[int, int]] = {}
    play.arrivals += [
        (spawn - OMEN_LEAD - 0.05, lambda: seen.setdefault('window', (len(play.sigils), len(play.strikes)))),
        (spawn - 0.001, lambda: seen.setdefault('spawn', (len(play.sigils), len(play.strikes)))),
        (spawn, appear(play, *pack)),
        (start + until, run.cancelled.set),
    ]
    play.arrivals.sort(key=lambda pair: pair[0])
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    return play, here, spot, order, seen


def test_off_the_strike_waits_for_the_pack(monkeypatch):
    play, _here, _spot, _order, seen = played(monkeypatch)
    assert seen['spawn'] == (0, 0)
    assert play.strikes  # the pack is fought once it shows


def test_the_strike_goes_on_the_spot_in_the_last_seconds_before_the_pack(monkeypatch):
    play, here, spot, _order, seen = played(monkeypatch, strike=True)
    assert seen['window'][1] == 0  # not before OMEN_LEAD
    early = play.strikes[: seen['spawn'][1]]
    assert early, 'no strike before the spawn'
    for unit, ground in early:
        assert unit is None  # nothing there yet
        assert abs(ground[1] - here[1]) < 2.0  # on the line to the spot
        assert here[0] < ground[0] <= spot[0] + 1.0


def test_the_sigil_goes_first_on_the_line_to_a_spot_off_the_screen(monkeypatch):
    # 24 east: the spot is off the screen; the sigil goes on its line as far as the screen lets the pointer
    play, here, spot, order, seen = played(monkeypatch, strike=True, sigil=True, away=24.0)
    assert seen['window'] == (1, 0)
    assert order[0] == 'sigil'
    laid = play.sigils[0]
    assert abs(laid[1] - here[1]) < 2.0
    assert 12.0 < math.dist(laid, here) < math.dist(spot, here)
    assert seen['spawn'][1] > 0  # then the strike, before the pack


def test_the_omen_sigil_alone_is_laid_once_before_the_pack(monkeypatch):
    _play, _here, _spot, _order, seen = played(monkeypatch, sigil=True)
    assert seen['spawn'] == (1, 0)


def test_a_fight_s_line_goes_through_the_spot_in_the_window_only(monkeypatch):
    monkeypatch.setattr(hunt_module, 'OMEN_STRIKE', True)
    play = game()
    hunt = hunter(play)
    here = (5000.0, 5000.0)
    spot, read = (5020.0, 5000.0), 100.0
    hunt.omens = {spot: read + OMEN_SECONDS}
    spawn = read + OMEN_SPAWN
    assert hunt.omen_focal(here, spawn - OMEN_LEAD - 0.1, []) is None
    assert hunt.omen_focal(here, spawn - OMEN_LEAD + 0.1, []) == spot
    assert hunt.omen_focal(here, spawn + OMEN_GRACE + 0.1, []) is None
    member = foe(30, 5020.0, 5000.0, flags=MINION, tier=5)
    assert hunt.omen_focal(here, spawn, [member]) is None  # the pack shows: the fight's own choice
    assert hunt.omen_focal((4970.0, 5000.0), spawn, []) is None  # beyond OMEN_OPEN_REACH
    monkeypatch.setattr(hunt_module, 'OMEN_STRIKE', False)
    assert hunt.omen_focal(here, spawn, []) is None


@pytest.mark.parametrize('ahead', [False, True])
def test_the_before_strike_rows_before_the_press(monkeypatch, ahead):
    # A leader in reach: the sigil opener's early row (buffs.py SIGIL_OPENER) is a before-strike row. Off, it is asked
    # from the bout's second look, after the strike's first cast; with AHEAD_BEFORE_PRESS at the first, before it.
    monkeypatch.setattr(plan, 'SIGIL_OPENER', True)
    monkeypatch.setattr(hunt_module, 'AHEAD_BEFORE_PRESS', ahead)
    play = game(foe(10, 5012.0, 5000.0, flags=CHAMPION, life=900, max_life=900))
    play.toughness[10] = 50  # it stands the bout out
    hunt = hunter(play)
    order: list[str] = []
    play.sigils, play.strikes = Logged('sigil', order), Logged('strike', order)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((play.clock.now + 3.0, run.cancelled.set))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    assert 'sigil' in order
    assert 'strike' in order
    assert (order.index('sigil') < order.index('strike')) == ahead
