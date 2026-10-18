"""A Herald in reach is the first target of Death Mark and of Sigil: Lethargy (the player, 01:01 on 2026-10-18:
"prioritizing keeping herald on sigil lethargy + death mark"; a tier 5 Apparition Herald's pack killed the character at
00:54:55 with its mark laid 1 s before)."""

from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import HERALD_SIGIL_SECONDS, prey, sigil_due
from inventory_tracking.builds.warlock.mark import MARK_SECONDS, herald, target, why_not
from inventory_tracking.builds.warlock.skills import DEATH_MARK, SIGIL_LETHARGY
from inventory_tracking.macros.build import BuffFacts
from inventory_tracking.macros.world import DEFILER_CLASS, Monster
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, player, world


UNIQUE, MINION = 0x08, 0x10
HERE = (5000.0, 5000.0)


def monster(unit: int, x: float, *, flags: int = 0, tier: int = 0) -> Monster:
    return Monster(unit, 41, 1, HERE[0] + x, HERE[1], 0xFFFFFFFF, flags, life=128, max_life=128, tier=tier)


def facts(reachable: list[Monster], cast_at=None, now: float = 100.0) -> BuffFacts:
    me = player(6)
    defiler = Monster(9, DEFILER_CLASS, 1, HERE[0] + 2.0, HERE[1], me.unit_id, ally=True)
    seen = world(6, slots=HUNT_SLOTS, monsters=(*reachable, defiler))
    return BuffFacts(seen, now, tuple(reachable), tuple(reachable), reachable[0] if reachable else None,
                     cast_at or {}, draws={})  # fmt: skip


def test_a_herald_in_reach_is_marked_first_whatever_the_price_and_again_once_its_mark_runs_out():
    near = monster(1, 4.0, flags=UNIQUE)  # a unique of no Herald's, nearer
    minion = monster(2, 6.0, flags=MINION, tier=5)
    boss = monster(3, 12.0, flags=UNIQUE, tier=5)
    assert herald(boss)
    assert not herald(minion)
    assert not herald(near)
    assert target(facts([near, minion, boss])) == boss
    assert why_not(facts([boss]), boss) is None  # no price asked: draws={} prices nothing
    marked = {(DEATH_MARK, boss.unit_id): 100.0 - 1.0, (DEATH_MARK, None): 99.0}
    assert target(facts([near, minion, boss], marked)) != boss  # its mark lasts
    late = {(DEATH_MARK, boss.unit_id): 100.0 - MARK_SECONDS - 0.1, (DEATH_MARK, None): 50.0}
    assert target(facts([near, minion, boss], late)) == boss


def test_the_sigil_goes_under_a_herald_in_reach_and_again_as_it_moves():
    minion = monster(2, 6.0, flags=MINION, tier=5)
    boss = monster(3, 12.0, flags=UNIQUE, tier=5)
    found = facts([minion, boss])  # the strike aimed through the minion
    assert prey(found) == boss
    assert sigil_due(found)
    laid = {(SIGIL_LETHARGY, boss.unit_id): 100.0 - HERALD_SIGIL_SECONDS + 1.0}
    assert not sigil_due(facts([minion, boss], laid))
    assert sigil_due(facts([minion, boss], laid, now=100.0 + 1.5))
    assert prey(replace(found, reachable=(minion,))) == minion  # no Herald: the strike's prey


# F3 of rca/2026-10-18/andariel-cadence-findings.md §5 (the player, 18:00 on 2026-10-18: "F3: let's test it"): no sigil
# while the run's boss is in reach and nothing hurts; the Herald's sigil stays (buffs.py QUIET_BY_THE_BOSS).


def andariel(unit: int = 4, x: float = 10.0) -> Monster:
    return Monster(unit, 156, 1, HERE[0] + x, HERE[1], 0xFFFFFFFF, UNIQUE, life=6000, max_life=6000)


def test_no_sigil_by_the_runs_boss_while_nothing_hurts(monkeypatch):
    from inventory_tracking.macros import buffs

    monkeypatch.setattr(buffs, 'QUIET_BY_THE_BOSS', True)
    her = andariel()
    elite = monster(5, 6.0, flags=UNIQUE)  # one of her pack, the strike aimed through it
    for reachable in ([her], [elite, her]):
        unhurt = replace(facts(reachable), hurt=lambda: False)
        assert not sigil_due(unhurt), reachable
        assert sigil_due(replace(unhurt, hurt=lambda: True)), reachable  # a loss of life: the sigil as before
        assert sigil_due(replace(unhurt, hurt=None)), reachable  # not known: as before
    # An elite away from her: the sigil as before
    assert sigil_due(replace(facts([elite]), hurt=lambda: False))
    # A Herald in reach keeps its sigil, by her or not (the player, 01:01 on 2026-10-18)
    boss = monster(3, 12.0, flags=UNIQUE, tier=5)
    with_herald = replace(facts([boss, her]), hurt=lambda: False)
    assert prey(with_herald) == boss
    assert sigil_due(with_herald)


def test_the_sigil_by_the_boss_is_todays_with_the_switch_off(monkeypatch):
    from inventory_tracking.macros import buffs

    monkeypatch.setattr(buffs, 'QUIET_BY_THE_BOSS', False)
    asked: list[bool] = []
    unhurt = replace(facts([andariel()]), hurt=lambda: asked.append(True) or False)
    assert sigil_due(unhurt)
    assert asked == []  # off, the life is not read for it
