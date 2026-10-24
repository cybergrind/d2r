"""The arena's side-effect-free look (game.py `peek`, PURE_BINDS; 2026-10-24, rca/2026-10-23/realtime-3-findings.md
§3): a bind's extra look sees the world as it stands and changes nothing, where `read` is a look with the game's time
in it (a walk asked during a cast begins at the look that finds the cast over)."""

from inventory_tracking.macros import binding
from inventory_tracking.macros.teleport import WALKING
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.game import pure_binds
from tests.inventory_tracking.scenarios.arena.scenes_basic import HERE
from tests.inventory_tracking.scenarios.arena.test_game import RIGHT_BUTTON, click, frames, point_at
from tests.inventory_tracking.scenarios.arena.test_moves import empty, mode


def test_a_peek_after_a_cast_begins_no_walk_and_a_read_does():
    arena = empty()
    arena.keys.button(RIGHT_BUTTON, True)
    frames(arena, 1)
    arena.keys.button(RIGHT_BUTTON, False)
    cast_ends = arena.acting_until
    assert cast_ends is not None
    point_at(arena, (HERE[0] + 6.0, HERE[1]))
    click(arena)
    while arena.clock.now < cast_ends:
        frames(arena, 1)
    held = (arena.acting_until, arena.bound, list(arena.route), arena.world)
    for _ in range(3):
        seen = arena.peek()
        assert seen.player is not None
        assert (seen.player.x, seen.player.y) == HERE
    assert (arena.acting_until, arena.bound, list(arena.route), arena.world) == held  # nothing stored
    arena.read()  # the look with the game's time: the walk asked for begins
    assert mode(arena) in WALKING


def test_pure_binds_routes_a_binds_look_to_the_peek_for_the_block_only(monkeypatch):
    arena = empty()
    looked = binding.newest_world
    monkeypatch.setattr(game, 'PURE_BINDS', True)
    with pure_binds(arena):
        assert binding.newest_world is not looked
        assert binding.newest_world(object()) == arena.peek()
        assert binding.newest_world(object(), light=True) == arena.peek()
    assert binding.newest_world is looked


def test_off_a_bind_looks_as_before():
    arena = empty()
    looked = binding.newest_world
    assert not game.PURE_BINDS
    with pure_binds(arena):
        assert binding.newest_world is looked
