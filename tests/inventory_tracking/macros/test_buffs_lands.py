"""Whether a checked cast lands (macros/buffs.py `Buffs.lands`): what macros/safety.py DRAW_CASTABLE prices holding
with the build's draw by (rca/2026-10-21/herald-fight-findings.md: three Death Mark keys on a tier 5 Herald took on
no monster, and holding was still priced as if the pack had turned to the demons)."""

from dataclasses import replace

from tests.inventory_tracking.macros.test_buffs import BOLT, MARKED, NEAR, ask, cast_on, checked


WITHIN = 11.76  # a Death Mark's hold (builds/warlock/mark.py MARK_SECONDS)
BESIDE = replace(NEAR, unit_id=17, x=NEAR.x + 1.0)  # a neighbour of the target the cast may go on instead


def test_with_no_cast_settled_the_draw_is_taken_to_land() -> None:
    play, buffs, _, _ = checked(NEAR)
    assert buffs.lands(BOLT, play.clock.now, WITHIN)


def test_a_cast_that_took_nowhere_does_not_land_until_its_hold_is_over() -> None:
    play, buffs, run, _ = checked(NEAR)
    cast_on(play, buffs, run)
    ask(play, buffs, run, 0.9)
    assert not buffs.lands(BOLT, play.clock.now, WITHIN)
    assert buffs.lands(BOLT, play.clock.now + WITHIN, WITHIN)


def test_a_cast_that_showed_on_its_target_lands() -> None:
    play, buffs, run, words = checked(NEAR)
    cast_on(play, buffs, run)
    words[NEAR.unit_id] = MARKED
    ask(play, buffs, run, 0.4)
    assert buffs.lands(BOLT, play.clock.now, WITHIN)


def test_a_cast_that_went_on_a_neighbour_lands_the_companions_went_there() -> None:
    play, buffs, run, words = checked(NEAR, BESIDE)
    cast_on(play, buffs, run)
    words[BESIDE.unit_id] = MARKED
    ask(play, buffs, run, 0.9, foes=(NEAR, BESIDE))
    assert buffs.missed  # not on the target
    assert buffs.lands(BOLT, play.clock.now, WITHIN)


def test_a_later_cast_that_took_ends_the_doubt() -> None:
    play, buffs, run, words = checked(NEAR)
    cast_on(play, buffs, run)
    ask(play, buffs, run, 0.9)
    assert not buffs.lands(BOLT, play.clock.now, WITHIN)
    cast_on(play, buffs, run)
    words[NEAR.unit_id] = MARKED
    ask(play, buffs, run, 0.4)
    assert buffs.lands(BOLT, play.clock.now, WITHIN)
