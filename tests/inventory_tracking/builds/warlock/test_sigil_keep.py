"""A dangerous monster kept in its sigil (builds/warlock/buffs.py SIGIL_KEEPS, casters.py `sigil`): the player,
2026-10-20 ~23:05, of Diablo's fight at 23:01:55 ("he moved outside the sigil lethargy and we never recasted it.
probably, for hard/dangerous enemies - we want to keep them under sigil's effect all the time")."""

from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock import buffs as plan
from inventory_tracking.builds.warlock.buffs import (
    BUFFS,
    HERALD_SIGIL_SECONDS,
    SIGIL_EARLY,
    SIGIL_GAP,
    SIGIL_LASTS,
    SIGIL_LOOK,
    SIGIL_RADIUS,
    SIGIL_SECONDS,
    SIGIL_SHOWS,
    SIGIL_STATE,
    SIGIL_UNSHOWN,
    dangerous,
    sigil_due,
)
from inventory_tracking.builds.warlock.casters import watch_of
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import SIGIL_LETHARGY
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, WINDOW, Game, character_of, world


ROW = next(row for row in BUFFS if row.skill == SIGIL_LETHARGY and row.before_strike is None)  # the late row
UNIQUE, CHAMPION, MINION = 0x08, 0x0C, 0x10
DIABLO = Monster(50, 243, 1, 5008.0, 5000.0, 0xFFFFFFFF, UNIQUE, life=30000, max_life=30000)  # flags 8 in the take
# A tier 3 Herald: a tier 4-5 pack's sigil goes by the pack's cover since 2026-10-21 (combat/pack.py SIGIL_COVER,
# test_pack_sigil.py); the Herald-centred rules below stay for the tiers under 4
HERALD = Monster(60, 41, 1, 5008.0, 5000.0, 0xFFFFFFFF, UNIQUE, life=128, max_life=128, tier=3)
CHAMP = Monster(70, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, CHAMPION, life=128, max_life=128)
PLAIN = Monster(80, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, life=128, max_life=128)


class Fight:
    """One monster in reach of the character at (5000, 5000) in the Chaos Sanctuary, and the fight's sigil row asked
    as the hunt asks it (macros/hunt.py: due, then the cast)."""

    def __init__(self, monster: Monster, now: float = 100.0) -> None:
        self.play = Game(world(area=108, slots=HUNT_SLOTS, monsters=(monster,)))
        self.play.clock.now = now
        self.buffs, self.run = Buffs(ECHOING_STRIKE_BUILD), self.play.run()
        self.unit = monster.unit_id

    @property
    def monster(self) -> Monster:
        return next(m for m in self.play.world.monsters if m.unit_id == self.unit)

    def move(self, x: float, y: float = 5000.0) -> None:
        self.play.world = replace(self.play.world, monsters=(replace(self.monster, x=x, y=y),))

    @property
    def laid_at(self) -> float:
        """The clock of the last sigil's key."""
        at = watch_of(self.buffs).at
        assert at is not None
        return at

    def look(self, at: float) -> bool:
        """The fight's look at clock `at` (or now, when a cast took the clock past it): whether a sigil was laid."""
        self.play.clock.now = max(at, self.play.clock.now)
        prey = self.monster
        facts = self.buffs.facts(self.run, self.play.world, (prey,), (prey,), prey)
        due = self.buffs.due(self.run, ROW, facts)
        if due is None:
            return False
        before = len(self.play.sigils)
        self.buffs.cast(self.run, due, lambda w, skills: {s: KEYS[s] for s in skills}, WINDOW[2] / WINDOW[3])
        return len(self.play.sigils) > before

    def looks(self, start: float, end: float, every: float = 0.1) -> list[float]:
        """The clocks of the sigils laid by looks every `every` s from `start` to `end`."""
        laid, at = [], start
        while at <= end:
            if self.look(at):
                laid.append(self.laid_at)
            at = round(at + every, 3)
        return laid


def words(shows: bool) -> bytes:
    """State words (game/layout.py STATE_RUN) with or without the sigil's state."""
    found = bytearray(32)
    if shows:
        found[SIGIL_STATE // 8] |= 1 << SIGIL_STATE % 8
    return bytes(found)


def test_the_dangerous_monsters_are_the_bosses_heralds_and_leaders():
    assert dangerous(DIABLO)
    assert dangerous(replace(DIABLO, flags=0))  # a boss by his class alone (macros/goals.py `is_boss`)
    assert dangerous(HERALD)
    assert dangerous(CHAMP)  # a leader, while the mark goes on leaders (mark.py MARK_LEADERS)
    assert not dangerous(PLAIN)
    assert not dangerous(replace(PLAIN, flags=MINION, tier=5))  # a Herald's minion


def test_diablo_stepping_out_of_his_sigil_gets_a_new_one_at_once():
    fight = Fight(DIABLO)
    assert fight.look(100.0)
    assert fight.play.sigils[0] == pytest.approx((5008.0, 5000.0), abs=1.5)
    assert fight.looks(100.1, 103.0) == []  # he stands in it
    fight.move(5008.0 + SIGIL_RADIUS + 2.0)  # he walks out of it
    assert len(fight.looks(103.1, 103.6)) == 1  # at the next look
    assert fight.laid_at - 103.1 < SIGIL_LOOK
    assert fight.play.sigils[1] == pytest.approx((5016.0, 5000.0), abs=1.5)  # under him where he stands now
    assert fight.looks(103.2, 106.0) == []  # in the new one


def test_one_stepping_out_at_once_waits_for_the_gap():
    fight = Fight(DIABLO)
    assert fight.look(100.0)
    first = fight.laid_at
    fight.move(5020.0)
    laid = fight.looks(100.1, 102.5)
    assert len(laid) == 1
    assert first + SIGIL_GAP <= laid[0] <= first + SIGIL_GAP + 0.3


def test_diablo_still_inside_gets_none_before_the_sigil_runs_out():
    fight = Fight(DIABLO)
    assert fight.look(100.0)
    fight.move(5008.0 + SIGIL_RADIUS - 1.0)  # walking about inside it
    ends = fight.laid_at + SIGIL_LASTS - SIGIL_EARLY
    assert fight.looks(100.1, ends - 0.05) == []
    laid = fight.looks(ends - 0.04, ends + 1.0)  # as it runs out: at the next look, before it has
    assert len(laid) == 1
    assert ends <= laid[0] <= ends + SIGIL_LOOK + 0.35 < fight.laid_at + SIGIL_EARLY
    assert SIGIL_SECONDS < SIGIL_LASTS - SIGIL_EARLY  # before 2026-10-20 he had another at SIGIL_SECONDS


def test_the_state_words_say_whether_he_stands_in_it():
    fight = Fight(DIABLO)
    shown = {'now': True}
    fight.run.unit_states = lambda m: words(shown['now'])
    assert fight.look(100.0)
    fight.move(5008.0 + SIGIL_RADIUS + 3.0)  # by the place he is out, but his state shows the sigil: in
    assert fight.looks(100.1, 103.0) == []
    fight.move(5008.0)
    shown['now'] = False  # back on the spot, and the state no longer shows it
    assert len(fight.looks(103.1, 103.6)) == 1
    again = fight.laid_at
    assert fight.looks(again, again + SIGIL_SHOWS - 0.05) == []  # the new one's state is not asked before it shows


def test_a_monster_whose_state_never_shows_the_sigil_is_judged_by_place():
    fight = Fight(DIABLO)
    fight.run.unit_states = lambda m: words(False)
    laid = fight.looks(100.0, 106.0)
    assert len(laid) == 1 + SIGIL_UNSHOWN  # the first, then again for each unshown state, then by place: in it
    assert all(b - a >= SIGIL_SHOWS for a, b in pairwise(laid))


def test_the_missile_read_says_where_the_sigil_lies():
    fight = Fight(DIABLO)
    lying: dict[str, tuple[float, float] | None] = {'at': (5008.0, 5000.0)}

    def flights(kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        at = lying['at']
        return ((1, 686, *at),) if at is not None else ()

    fight.run.flights = flights
    assert fight.look(100.0)
    assert fight.looks(100.1, 102.0) == []
    lying['at'] = (5020.0, 5000.0)  # it lies elsewhere than it was aimed: he is out of it
    assert len(fight.looks(102.1, 102.6)) == 1
    lying['at'] = None  # none of the character's in flight
    after = fight.laid_at
    laid = fight.looks(after, after + SIGIL_GAP + 0.6)
    assert len(laid) == 1
    assert laid[0] >= after + SIGIL_GAP


def test_a_new_level_or_game_has_no_sigil_lying():
    fight = Fight(DIABLO)
    assert fight.look(100.0)
    fight.play.world = replace(fight.play.world, player=replace(character_of(fight.play.world), area=107))
    assert fight.look(101.5)
    fight.play.clock.now = 50.0  # another game's clock, gone back
    assert watch_of(fight.buffs).age(50.0) < 0
    assert not watch_of(fight.buffs).lies(50.0, 107)


def test_the_sigil_goes_where_the_monster_stands_at_the_key():
    fight = Fight(DIABLO)
    prey = fight.monster
    facts = fight.buffs.facts(fight.run, fight.play.world, (prey,), (prey,), prey)  # the look before
    due = fight.buffs.due(fight.run, ROW, facts)
    assert due is not None
    fight.move(5014.0, 5004.0)  # he walked on while a Death Mark was cast
    fight.buffs.cast(fight.run, due, lambda w, skills: {s: KEYS[s] for s in skills}, WINDOW[2] / WINDOW[3])
    assert fight.play.sigils == [pytest.approx((5014.0, 5004.0), abs=1.5)]


def test_a_herald_inside_its_sigil_gets_one_at_least_as_often_as_before():
    fight = Fight(HERALD)
    assert fight.look(100.0)
    first = fight.laid_at
    laid = fight.looks(100.1, 100.0 + 2 * HERALD_SIGIL_SECONDS + 1.5)  # standing in it
    assert len(laid) == 2
    # as before 2026-10-20: one when the last under it is HERALD_SIGIL_SECONDS old (within a look of 0.1 s and a cast)
    assert all(HERALD_SIGIL_SECONDS < b - a <= HERALD_SIGIL_SECONDS + 0.3 for a, b in pairwise([first, *laid]))


def test_a_herald_never_under_a_sigil_gets_one_at_once_inside_another():
    fight = Fight(CHAMP)
    assert fight.look(100.0)
    herald = replace(HERALD, x=5009.0)  # walks up inside the champion's sigil
    fight.play.world = replace(fight.play.world, monsters=(fight.monster, herald))
    fight.unit = herald.unit_id
    first = fight.laid_at
    laid = fight.looks(first + SIGIL_GAP, first + SIGIL_GAP + 0.5)
    assert len(laid) == 1
    assert laid[0] - first < SIGIL_GAP + 0.3


def test_trash_gets_no_sigil():
    fight = Fight(PLAIN)
    assert fight.looks(100.0, 130.0, every=0.5) == []
    facts = fight.buffs.facts(fight.run, fight.play.world, (PLAIN,), (PLAIN,), PLAIN)
    assert not sigil_due(facts)


def test_a_leader_not_kept_and_the_switch_off_go_by_the_old_clock(monkeypatch):
    monkeypatch.setattr(plan, 'MARK_LEADERS', False)  # the mark's leaders off: a champion is no dangerous monster
    fight = Fight(CHAMP)
    laid = fight.looks(100.0, 100.0 + 2 * SIGIL_SECONDS + 0.9)
    assert len(laid) == 3
    assert all(SIGIL_SECONDS < b - a <= SIGIL_SECONDS + 0.4 for a, b in pairwise(laid))
    monkeypatch.setattr(plan, 'SIGIL_KEEPS', False)
    fight = Fight(DIABLO)
    fight.move(5008.0 + SIGIL_RADIUS + 3.0)  # out of it: no new one before SIGIL_SECONDS, as before 2026-10-20
    laid = fight.looks(100.0, 100.0 + SIGIL_SECONDS + 0.9)
    assert len(laid) == 2
    assert SIGIL_SECONDS < laid[1] - laid[0] <= SIGIL_SECONDS + 0.4
