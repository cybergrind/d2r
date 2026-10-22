"""Sigil: Lethargy with a tier 4-5 Herald pack (combat/pack.py SIGIL_COVER, builds/warlock/buffs.py `sigil_due`/`prey`,
casters.py `sigil`). The player, 2026-10-21 ~09:40: "sigil of lethargy to slow whole group"; 2026-10-20 ~23:05: "keep
them under sigil's effect all the time". The sigil goes at the disc that covers the most of the pack (the Herald
weighted twice), on the demon once it holds the pack, and again when the one that lies covers under half of the pack
or runs out (rca/2026-10-21/herald-fight-findings.md §2 step 3, §3.1 ENGAGE 3 and HOLD)."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan
from inventory_tracking.builds.warlock.buffs import BUFFS, SIGIL_EARLY, SIGIL_GAP, SIGIL_LASTS, SIGIL_RADIUS
from inventory_tracking.builds.warlock.casters import watch_of
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import SIGIL_LETHARGY
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, WINDOW, Game, world


ROW = next(row for row in BUFFS if row.skill == SIGIL_LETHARGY)
NOBODY = 0xFFFFFFFF
UNIQUE, MINION = 0x08, 0x10
GREAT_MARSH = 77


def hulk(unit: int, x: float, y: float, flags: int = MINION, tier: int = 5) -> Monster:
    return Monster(unit, 128, 1, x, y, NOBODY, flags, life=128, max_life=128, tier=tier)


def demon(unit: int, txt: int, x: float, y: float) -> Monster:
    return Monster(unit, txt, 1, x, y, NOBODY, 0, ally=True, life=128, max_life=230)


# The character at (5000, 5000); the Herald 17 off to the north-east, alone; five minions bunched 11 off to the
# south-east, 18 from the Herald: the disc on the five covers more than the one under the Herald (weight 2).
HERALD = hulk(1, 5016.0, 4994.0, UNIQUE)
BUNCH = tuple(
    hulk(10 + k, 5006.0 + dx, 5009.0 + dy) for k, (dx, dy) in enumerate(((0, 0), (1, 1), (-1, 1), (1, -1), (0, 2)))
)
BY_ME = (demon(70, 744, 5001.0, 5000.5), demon(71, 189, 5000.0, 5001.0))


class Fight:
    """The pack in reach of the character, the fight's sigil row asked as the hunt asks it (due, then the cast)."""

    def __init__(self, *monsters: Monster, now: float = 100.0) -> None:
        self.play = Game(world(area=GREAT_MARSH, slots=HUNT_SLOTS, monsters=monsters))
        self.play.clock.now = now
        self.buffs, self.run = Buffs(ECHOING_STRIKE_BUILD), self.play.run()

    def hostiles(self) -> tuple[Monster, ...]:
        return tuple(m for m in self.play.world.monsters if not m.ally)

    def place(self, *monsters: Monster) -> None:
        self.play.world = replace(self.play.world, monsters=monsters)

    def look(self, at: float) -> bool:
        self.play.clock.now = max(at, self.play.clock.now)
        foes = self.hostiles()
        facts = self.buffs.facts(self.run, self.play.world, foes, foes, foes[0] if foes else None)
        due = self.buffs.due(self.run, ROW, facts)
        if due is None:
            return False
        before = len(self.play.sigils)
        self.buffs.cast(self.run, due, lambda w, skills: {s: KEYS[s] for s in skills}, WINDOW[2] / WINDOW[3])
        return len(self.play.sigils) > before

    def looks(self, start: float, end: float, every: float = 0.1) -> list[tuple[float, float]]:
        laid, at = [], start
        while at <= end:
            if self.look(at):
                laid.append(self.play.sigils[-1])
            at = round(at + every, 3)
        return laid


def centre(*monsters: Monster) -> tuple[float, float]:
    return (sum(m.x for m in monsters) / len(monsters), sum(m.y for m in monsters) / len(monsters))


def test_the_pack_s_sigil_goes_at_the_disc_covering_the_most_of_it_not_under_the_herald():
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    assert fight.look(100.0)
    laid = fight.play.sigils[0]
    assert math.dist(laid, centre(*BUNCH)) < 2.5
    assert math.dist(laid, (HERALD.x, HERALD.y)) > SIGIL_RADIUS


def test_it_is_not_laid_again_while_half_the_pack_stands_in_it():
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    assert fight.look(100.0)
    ends = 100.0 + SIGIL_LASTS - SIGIL_EARLY
    assert fight.looks(100.1, ends - 0.2) == []


def test_it_is_laid_again_when_the_cover_drops_under_half_of_the_pack():
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    assert fight.look(100.0)
    moved = tuple(replace(m, x=m.x - 20.0) for m in BUNCH)  # the bunch walks out of it together, 26 from the Herald
    fight.place(HERALD, *moved, *BY_ME)
    laid = fight.looks(100.1, 100.0 + SIGIL_GAP + 0.6)
    assert len(laid) == 1
    assert math.dist(laid[0], centre(*moved)) < 2.5


def test_a_cover_that_no_disc_betters_is_kept():
    spread = tuple(
        hulk(20 + k, 5000.0 + 12.0 * math.cos(k * 1.2566), 5000.0 + 12.0 * math.sin(k * 1.2566)) for k in range(5)
    )
    fight = Fight(*spread, *BY_ME)
    assert fight.look(100.0)  # one member under it (no two stand within 12 of each other)
    assert fight.looks(100.1, 104.0) == []  # under half covered, but no disc covers more


def test_it_is_laid_again_as_it_runs_out():
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    assert fight.look(100.0)
    ends = 100.0 + SIGIL_LASTS - SIGIL_EARLY
    assert len(fight.looks(ends - 0.05, ends + 0.6)) == 1


def test_once_a_demon_holds_the_pack_the_sigil_goes_on_the_demon():
    holding = demon(70, 744, 5008.0, 5007.0)  # 10.6 off the character, among the bunch
    fight = Fight(HERALD, *BUNCH, holding, demon(71, 189, 5000.0, 5001.0))
    assert fight.look(100.0)
    assert fight.play.sigils[0] == pytest.approx((holding.x, holding.y), abs=1.5)


def test_a_herald_under_tier_4_keeps_the_herald_centred_sigil():
    herald = replace(HERALD, tier=3)
    bunch = tuple(replace(m, tier=3) for m in BUNCH)
    fight = Fight(herald, *bunch, *BY_ME)
    assert fight.look(100.0)
    assert fight.play.sigils[0] == pytest.approx((herald.x, herald.y), abs=1.5)
    assert watch_of(fight.buffs).unit == herald.unit_id


def test_with_the_switch_off_the_sigil_stays_under_the_herald(monkeypatch):
    monkeypatch.setattr(pack, 'SIGIL_COVER', False)
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    assert fight.look(100.0)
    assert fight.play.sigils[0] == pytest.approx((HERALD.x, HERALD.y), abs=1.5)


def test_the_pack_row_is_looked_at_every_sigil_look():
    fight = Fight(HERALD, *BUNCH, *BY_ME)
    foes = fight.hostiles()
    facts = fight.buffs.facts(fight.run, fight.play.world, foes, foes, foes[0])
    assert plan.sigil_due(facts)
    assert plan.prey(facts) == HERALD  # the row's anchor: the Herald in reach, the caster finds the spot


# -- the sigil at a Herald's coming (buffs.py OMEN_SIGIL; the player, 2026-10-21 ~20:42: "we can put sigil in advance
# before herald's packa spawning. then we could reposition in if required"): the omen shows a median 5.0 s before the
# pack, and a sigil there covers 61% of it in its first second (rca/2026-10-21/arachnid-herald-2-findings.md) --


def test_a_pending_omen_in_reach_gets_one_sigil_at_its_spot_before_the_pack_shows(herald2_on, monkeypatch) -> None:
    spider = Monster(2, 125, 1, 4980.0, 5000.0, NOBODY, 0, life=50, max_life=50)  # a plain one, behind
    fight = Fight(spider)
    spot = (5012.0, 5009.0)  # 15 from the character
    pack.saw_omens([(spot, 105.0)])
    assert fight.look(100.0)
    assert math.dist(fight.play.sigils[-1], spot) < 1.5
    assert fight.looks(100.1, 104.0) == []  # once: the pack's own sigil comes when it shows (`pack_anchor`)
    far = Fight(spider)
    pack.saw_omens([((5030.0, 5000.0), 105.0)])  # 30 away: beyond OMEN_SIGIL_REACH
    assert not far.look(100.0)
    monkeypatch.setattr(plan, 'OMEN_SIGIL', False)
    off = Fight(spider)
    pack.saw_omens([(spot, 105.0)])
    assert not off.look(100.0)


def test_with_the_pack_in_reach_the_omen_is_not_the_sigils_target(herald2_on) -> None:
    fight = Fight(*BUNCH)
    pack.saw_omens([((4990.0, 4990.0), 105.0)])
    assert fight.look(100.0)
    assert math.dist(fight.play.sigils[-1], (4990.0, 4990.0)) > SIGIL_RADIUS
