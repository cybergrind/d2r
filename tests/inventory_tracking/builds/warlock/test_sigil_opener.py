"""Sigil: Lethargy before the fight's first strike (builds/warlock/buffs.py SIGIL_OPENER, casters.py `opener_sigil`).
The player, 2026-10-23 ~19:35: "we're not putting lethargy before the fight started" (rca/2026-10-23/
sigil-opener-findings.md): one early sigil row, asked before the bout's first strike, for the fights the sigil was
already for (a leader, a boss, a Herald, a tier 4-5 pack) and for a group that drains mana or threatens OPENER_THREAT,
laid where that group will be OPENER_LEAD s on; off, the plan casts as before."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan
from inventory_tracking.builds.warlock.buffs import BUFFS, SIGIL_GAP, SIGIL_LASTS, SIGIL_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import SIGIL_LETHARGY
from inventory_tracking.combat.threats.manaburn import EXTRA_FAST, MANA_BURN
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, WINDOW, Game, world


EARLY = next(row for row in BUFFS if row.skill == SIGIL_LETHARGY and row.before_strike is not None)
LATE = next(row for row in BUFFS if row.skill == SIGIL_LETHARGY and row.before_strike is None)
NOBODY = 0xFFFFFFFF
CHAMPION, MINION = 0x04, 0x10
HORROR, FLAYER = 4, 398  # monstats: a melee walker; a blowgun shooter (terror/danger.py's table: ranged)
STRONG = 5
GREAT_MARSH = 77


@pytest.fixture(autouse=True)
def opener_on(monkeypatch):
    monkeypatch.setattr(plan, 'SIGIL_OPENER', True)


def horror(unit: int, x: float, y: float, mods: tuple[int, ...] = (), flags: int = MINION) -> Monster:
    return Monster(unit, HORROR, 2, x, y, NOBODY, flags, life=128, max_life=128, modifiers=mods)


def burners(dx: float = 15.0) -> tuple[Monster, ...]:
    """Five Horrors with Mana Burn bunched `dx` east of the character at (5000, 5000)."""
    spots = ((0.0, 0.0), (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (0.0, 2.0))
    return tuple(horror(10 + k, 5000.0 + dx + x, 5000.0 + y, (MANA_BURN,)) for k, (x, y) in enumerate(spots))


class Fight:
    """The hostiles in reach of the character, the fight's rows asked as the hunt asks them."""

    def __init__(self, *monsters: Monster, now: float = 100.0) -> None:
        self.play = Game(world(area=GREAT_MARSH, slots=HUNT_SLOTS, monsters=monsters))
        self.play.clock.now = now
        self.buffs, self.run = Buffs(ECHOING_STRIKE_BUILD), self.play.run()

    def facts(self, prey: Monster | None = None):
        foes = tuple(m for m in self.play.world.monsters if not m.ally)
        return self.buffs.facts(self.run, self.play.world, foes, foes, prey or (foes[0] if foes else None))

    def place(self, *monsters: Monster) -> None:
        self.play.world = replace(self.play.world, monsters=monsters)

    def look(self, at: float, row=EARLY, prey: Monster | None = None) -> bool:
        self.play.clock.now = max(at, self.play.clock.now)
        due = self.buffs.due(self.run, row, self.facts(prey))
        if due is None:
            return False
        before = len(self.play.sigils)
        self.buffs.cast(self.run, due, lambda w, skills: {s: KEYS[s] for s in skills}, WINDOW[2] / WINDOW[3])
        return len(self.play.sigils) > before


def test_off_the_early_row_is_never_due_and_the_late_one_is_as_before(monkeypatch):
    monkeypatch.setattr(plan, 'SIGIL_OPENER', False)
    leader = horror(1, 5012.0, 5000.0, flags=CHAMPION)
    fight = Fight(leader, *burners())
    facts = fight.facts(leader)
    assert not plan.opener_due(facts)
    assert EARLY.before_strike is not None
    assert not EARLY.before_strike(facts)
    assert fight.look(100.0, LATE, prey=leader)  # under the leader, as before
    assert math.dist(fight.play.sigils[0], (leader.x, leader.y)) < 2.0


def test_a_fight_the_sigil_was_for_gets_it_from_the_early_row_before_the_strike():
    leader = horror(1, 5012.0, 5000.0, flags=CHAMPION)
    fight = Fight(leader)
    facts = fight.facts(leader)
    assert plan.opener_due(facts)
    assert fight.buffs.before_strike(facts)
    assert fight.look(100.0, prey=leader)
    assert not fight.look(100.0, LATE, prey=leader)  # the late row knows it: not laid twice in a look
    assert math.dist(fight.play.sigils[0], (leader.x, leader.y)) < 2.0  # under it, kept in it as before


def test_mana_burners_get_one_before_the_strike_where_they_will_be():
    fight = Fight(*burners(15.0))
    facts = fight.facts()
    assert plan.opener_due(facts)
    assert fight.buffs.before_strike(facts)
    assert fight.look(100.0)
    laid = fight.play.sigils[0]
    middle = (5015.0, 5000.6)
    # led toward the character: nearer it than the pack stands now, the pack inside it once there
    assert math.dist(laid, (5000.0, 5000.0)) < math.dist(middle, (5000.0, 5000.0)) - 1.0
    found = plan.opening_of(facts)
    assert found is not None
    assert found.why.startswith('mana burners')
    assert plan.covers(found.spot, found) >= 0.8


def test_it_is_not_laid_again_while_the_one_that_lies_covers_the_group(monkeypatch):
    monkeypatch.setattr(plan, 'OPENER_ONCE', False)  # the early row's laying again (OPENER_ONCE: the late row's)
    fight = Fight(*burners(15.0))
    assert fight.look(100.0)
    assert not any(fight.look(100.0 + 0.1 * k) for k in range(1, 40))  # 4 s: held in it
    gone = tuple(replace(m, x=m.x - 30.0) for m in burners(15.0))  # the group comes round, 15 west: out of it
    fight.place(*gone)
    assert fight.look(104.0 + SIGIL_GAP)
    assert fight.play.sigils[-1][0] < 5000.0


def test_one_that_runs_out_is_laid_again():
    fight = Fight(*burners(15.0))
    assert fight.look(100.0)
    laid = fight.play.sigils[0]
    there = [replace(m, x=laid[0] + m.x - 5015.0, y=laid[1] + m.y - 5000.0) for m in burners(15.0)]  # in it
    fight.place(*there)
    assert not fight.look(110.0)
    assert fight.look(100.0 + SIGIL_LASTS - 0.5)


def test_a_weak_group_gets_none():
    plain = tuple(horror(20 + k, 5012.0 + k, 5000.0) for k in range(6))  # six Horrors: threat ~1
    fight = Fight(*plain)
    facts = fight.facts()
    assert plan.opening_of(facts) is None
    assert not plan.opener_due(facts)
    assert not fight.buffs.before_strike(facts)


def test_a_threatening_group_gets_one(monkeypatch):
    fast = tuple(horror(20 + k, 5012.0 + k, 5000.0, (EXTRA_FAST, STRONG)) for k in range(6))  # threat ~4.4
    monkeypatch.setattr(plan, 'OPENER_THREAT', 4.0)
    fight = Fight(*fast)
    found = plan.opening_of(fight.facts())
    assert found is not None
    assert found.why.startswith('the threat')
    assert fight.look(100.0)
    assert not plan.opening_of(Fight(*fast[:2]).facts())  # two of them: under the line


def test_a_melee_walker_is_led_to_its_contact_and_a_shooter_stands():
    here = (5000.0, 5000.0)
    walker = horror(1, 5020.0, 5000.0, (EXTRA_FAST,))
    ahead = plan.led(here, walker, (), 2.0)
    assert ahead[0] == pytest.approx(5000.0 + plan.OPENER_CONTACT)  # it stops beside the character
    shot = Monster(2, FLAYER, 2, 5020.0, 5000.0, NOBODY, MINION, life=128, max_life=128)
    assert plan.led(here, shot, (), 2.0) == (5020.0, 5000.0)
    held = plan.led(here, walker, [(5014.0, 5000.0)], 2.0)  # a demon between holds it: it goes for the demon
    assert held[0] == pytest.approx(5014.0 + plan.OPENER_CONTACT)


def test_the_disc_weighs_the_dangerous_members():
    # three plain Horrors west, two Mana Burn ones east 14 apart: the burners' disc outweighs (2 x 2 against 3)
    plain = tuple(horror(30 + k, 4990.0 + k, 5010.0) for k in range(3))
    burning = tuple(horror(40 + k, 5004.0 + k, 5010.0, (MANA_BURN,)) for k in range(2))
    spot = plan.disc([((m.x, m.y), plan.weight_of(m)) for m in (*plain, *burning)], SIGIL_RADIUS - 0.5)
    assert math.dist(spot, (5004.5, 5010.0)) < 2.0


def test_off_the_screen_the_early_row_is_not_due():
    # A due row whose caster declines still ends the look's casts under FIGHT_CAST_REACH's pace (one a look), and an
    # off-screen ground is declined: the early row is not due there; the late one asks as before.
    far = horror(1, 5200.0, 5000.0, flags=CHAMPION)
    fight = Fight(far)
    assert not plan.opener_due(fight.facts(far))
    assert plan.sigil_late(fight.facts(far))


def test_the_early_row_is_not_due_while_the_one_that_lies_holds_the_leader(monkeypatch):
    monkeypatch.setattr(plan, 'OPENER_ONCE', False)  # the early row's laying again (OPENER_ONCE: the late row's)
    leader = horror(1, 5012.0, 5000.0, flags=CHAMPION)
    fight = Fight(leader)
    assert fight.look(100.0, prey=leader)
    fight.play.clock.now = 100.0 + SIGIL_GAP + 0.5
    assert not plan.opener_due(fight.facts(leader))  # it stands in it: the late row keeps it as before
    away = replace(leader, x=5000.0, y=5012.0)  # it walks out, 17 from the sigil
    fight.place(away)
    assert plan.opener_due(fight.facts(away))


# -- OPENER_ONCE (2026-10-24, rca/2026-10-24/sigil-opener-2-findings.md): the early row lays a fight's first sigil only;
# the late row keeps it --


def test_once_the_early_row_lays_the_first_sigil_only():
    fight = Fight(*burners(15.0))
    assert fight.look(100.0)
    gone = tuple(replace(m, x=m.x - 30.0) for m in burners(15.0))  # out of it, as in the relay test
    fight.place(*gone)
    assert not plan.opener_due(fight.facts())  # one lies by the fight: not the early row's to lay again
    fight.play.clock.now = 100.0 + SIGIL_LASTS
    assert plan.opener_due(fight.facts())  # run out: the next fight's first
