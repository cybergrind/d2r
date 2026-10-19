"""The KP_6 loop's first played game, cyber17 (2026-10-16 02:48, rca/2026-10-16/loop-first-game-findings.md): the
requirements it showed unmet, held since the fix of that day."""

from inventory_tracking.macros.teleport import USES, classes
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.macros.world import USED, Thing
from tests.inventory_tracking.macros.fakes import Game, player, world


def test_every_class_a_marks_use_may_click_is_read_by_the_run():
    # 02:48:24-33: at the first camp chest's mark "Super chests is not here" 90 times, the class-181 chest at 0.0
    # units from the mark, closed (take 20261015T234817Z-79 `o`), until the player opened it by hand.
    missing = {use: sorted(classes(use) - USED) for use in USES if not classes(use) <= USED}
    assert missing == {}


def test_the_waypoint_is_over_once_the_game_takes_input_in_the_level_it_leads_to():
    # 02:48:17.5 Lower Kurast reached; three Swap Weapons and a Blade Warp sent in the next 3 s took nothing (the
    # frames' left skill unchanged, "the game took no cast"); the first input that took came 5.4 s after the arrival.
    play = Game(world(103, player=player(103, x=5048.0, y=5044.0)))
    play.thing, play.thing_above = Thing(6, 398, 2, 5044.0, 5019.0), 0.0
    play.arrival_load = 3.0

    travel(play.run(), 79)

    assert play.character.area == 79
    assert play.arrived_at is not None
    assert play.clock.now >= play.arrived_at + 3.0  # not handed on to the next leg while the game loads
