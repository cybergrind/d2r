"""A Herald in reach is the first target of Death Mark and of Sigil: Lethargy (the player, 01:01 on 2026-10-18:
"prioritizing keeping herald on sigil lethargy + death mark"; a tier 5 Apparition Herald's pack killed the character at
00:54:55 with its mark laid 1 s before)."""

from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import HERALD_SIGIL_SECONDS, SIGIL_LOOK, prey, sigil_due
from inventory_tracking.builds.warlock.mark import MARK_SECONDS, herald, target, why_not
from inventory_tracking.builds.warlock.skills import DEATH_MARK, SIGIL_LETHARGY
from inventory_tracking.game.layout import DEFILER_CLASS
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts
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
    # Kept in its sigil (SIGIL_KEEPS, 2026-10-20): the caster looks every SIGIL_LOOK whether it still stands in one
    # and casts at HERALD_SIGIL_SECONDS at the latest (test_sigil_keep.py)
    laid = {(SIGIL_LETHARGY, boss.unit_id): 100.0 - SIGIL_LOOK + 0.1}
    assert not sigil_due(facts([minion, boss], laid))
    assert sigil_due(facts([minion, boss], laid, now=100.0 + 0.5))
    assert SIGIL_LOOK < HERALD_SIGIL_SECONDS
    assert prey(replace(found, reachable=(minion,))) == minion  # no Herald: the strike's prey


# The player decided on 2026-10-18 to keep Sigil on all strong enemies, including bosses and Heralds.


def andariel(unit: int = 4, x: float = 10.0) -> Monster:
    return Monster(unit, 156, 1, HERE[0] + x, HERE[1], 0xFFFFFFFF, UNIQUE, life=6000, max_life=6000)


def test_sigil_is_due_for_a_boss_champion_and_unique_even_while_unhurt():
    her = andariel()
    champion = monster(5, 6.0, flags=0x0C)
    elite = monster(6, 8.0, flags=UNIQUE)
    for reachable in ([her], [champion], [elite], [elite, her]):
        unhurt = replace(facts(reachable), hurt=lambda: False)
        assert sigil_due(unhurt), reachable
        assert sigil_due(replace(unhurt, hurt=lambda: True)), reachable
        assert sigil_due(replace(unhurt, hurt=None)), reachable
    boss = monster(3, 12.0, flags=UNIQUE, tier=5)
    with_herald = replace(facts([boss, her]), hurt=lambda: False)
    assert prey(with_herald) == boss
    assert sigil_due(with_herald)
