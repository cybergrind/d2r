"""A wait a hostile hitting the character ends (macros/threat.py, rca/2026-10-23/pause-findings.md)."""

from types import SimpleNamespace

import pytest

from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster, Player, World
from inventory_tracking.macros import threat
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.native.layout import LIFE_STAT


def player(life_at: int = 0x100) -> Player:
    return Player(1, 'CybergrindAA', 1, 108, 5000.0, 5000.0, None, stats_at=life_at)


def monster(x: float, *, ally: bool = False, owner: int = NO_OWNER, mode: int = 1) -> Monster:
    return Monster(9, 19, mode, x, 5000.0, owner, 0, ally)


class Fake:
    """A run whose clock moves by its sleeps, whose life falls `drop` points a look from `hit_at` on."""

    def __init__(self, monsters, *, drop=0, hit_at=0.0):
        self.now, self.slept, self.life = 0.0, [], 2000
        self.monsters, self.drop, self.hit_at = monsters, drop, hit_at
        self.pace = SimpleNamespace(sleep=self.sleep)
        self.unit_stats = lambda at: {LIFE_STAT: self.life << 8}

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds

    def clock(self):
        return self.now

    def world(self):
        if self.now >= self.hit_at:
            self.life -= self.drop
        return World(True, (), 'game', (), player=player(), monsters=tuple(self.monsters))


def test_a_hostile_hitting_the_character_ends_the_wait_as_beset():
    run = Fake([monster(5006.0)], drop=40, hit_at=0.3)
    with pytest.raises(Abort, match='hit during the wait') as stop:
        threat.watched_sleep(run, 2.0, 'the wait')  # pyrefly: ignore[bad-argument-type] a fake run: clock, sleeps, looks
    assert stop.value.cause == 'beset'
    assert 0.3 <= run.now <= 0.4  # one frame after the first blow, not the whole 2 s


@pytest.mark.parametrize(
    ('monsters', 'drop'),
    [
        ([monster(5006.0)], 0),  # near, no blow: the wait goes on
        ([monster(5030.0)], 40),  # a blow, the hostile far: not this wait's (a missile; the watchdog's)
        ([monster(5003.0, ally=True)], 40),  # the Defiler's own price, an ally beside
        ([monster(5003.0, owner=7)], 40),  # the mercenary
        ([monster(5003.0, mode=12)], 40),  # a corpse
    ],
)
def test_the_wait_is_slept_out_without_a_hostile_hitting(monsters, drop):
    run = Fake(monsters, drop=drop)
    threat.watched_sleep(run, 1.0, 'the wait')  # pyrefly: ignore[bad-argument-type] a fake run: clock, sleeps, looks
    assert run.now == pytest.approx(1.0)


def test_off_it_is_the_plain_sleep(monkeypatch):
    monkeypatch.setattr(threat, 'WATCHED_WAITS', False)
    run = Fake([monster(5006.0)], drop=40)
    threat.watched_sleep(run, 2.0, 'the wait')  # pyrefly: ignore[bad-argument-type] a fake run: clock, sleeps, looks
    assert run.slept == [2.0]


def test_a_clock_the_sleep_does_not_move_still_ends_the_wait():
    # The slices are counted: a fake run whose clock stands (the loop's tests) once looped here for ever
    run = Fake([monster(5006.0)])
    run.clock = lambda: 0.0
    threat.watched_sleep(run, 1.0, 'the wait')  # pyrefly: ignore[bad-argument-type] a fake run: clock, sleeps, looks
    assert sum(run.slept) == pytest.approx(1.0)
    assert len(run.slept) == 25
