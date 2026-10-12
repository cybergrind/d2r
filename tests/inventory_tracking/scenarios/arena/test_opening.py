"""What the first seconds of a fight cost in the arena (game.py): a stagger, a block, a buff's cast, a chest
with a monster before it. Each is there because the incident `infector-seal` had it (incident.py)."""

import random

import pytest

from inventory_tracking.builds.warlock.skills import PSYCHIC_WARD
from inventory_tracking.macros.world import MONSTER_UNIT, OBJECT_UNIT
from tests.inventory_tracking.macros.fakes import KEYS
from tests.inventory_tracking.scenarios.arena.evidence.sure import sure
from tests.inventory_tracking.scenarios.arena.game import (
    BLOCK_SECONDS,
    BLOCKING,
    CASTING,
    QUICK_CAST_SECONDS,
    RECOVERY_SECONDS,
    STAGGERED,
    Arena,
)
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.scene import Prop, Scene
from tests.inventory_tracking.scenarios.arena.scenes_basic import HELL_BOVINE, HERE, LIFE, hero, mob, one_in_the_open
from tests.inventory_tracking.scenarios.arena.test_game import (
    FRAME,
    RIGHT_BUTTON,
    click,
    frames,
    place,
    point_at,
    strong,
    tap,
)


CHEST = 125  # objects.txt InnerHellObject1, the chest of the incident (macros/data/containers.json)
LIFT = 45.0 / 16  # units: `Game.thing_above`, how far above its ground an object's picture is clicked


def blows(arena: Arena, *points: float) -> None:
    """The monsters' blows of the next ticks are `points`, then nothing."""
    left = list(points)
    arena.mobs.tick = lambda *given: left.pop(0) if left else 0.0  # type: ignore[method-assign]


def mode(arena: Arena) -> int:
    stand = arena.world.player
    assert stand is not None
    return stand.mode


def test_a_blow_of_a_twelfth_of_the_life_staggers_and_a_lighter_one_does_not():
    arena = Arena(one_in_the_open())
    blows(arena, LIFE / 12 - 1)
    frames(arena, 1)
    assert mode(arena) != STAGGERED
    blows(arena, LIFE / 12)
    frames(arena, 1)
    assert mode(arena) == STAGGERED
    assert arena.staggers == 1
    frames(arena, round(RECOVERY_SECONDS / FRAME) + 2)
    assert mode(arena) != STAGGERED


def test_nothing_is_cast_while_the_character_staggers_and_the_strike_goes_on_after():
    arena = Arena(one_in_the_open())
    point_at(arena, place(arena, 1))
    blows(arena, LIFE / 12)
    frames(arena, 1)
    arena.keys.button(RIGHT_BUTTON, True)
    frames(arena, round(RECOVERY_SECONDS / FRAME) - 2)
    assert arena.casts == 0
    frames(arena, 6)
    assert arena.casts == 1


def test_a_stagger_loses_the_cast_whose_blades_are_not_born():
    arena = Arena(one_in_the_open())
    point_at(arena, place(arena, 1))
    arena.keys.button(RIGHT_BUTTON, True)
    arena.read()
    assert len(arena.flights) == 1
    assert arena.flights[0].birth > arena.time.ticks
    blows(arena, LIFE / 12)
    frames(arena, 1)
    assert arena.flights == []


def test_a_blocked_blow_takes_nothing_and_holds_the_character_for_the_blocks_length(monkeypatch):
    sure(monkeypatch)
    scene = Scene('contact', hero(), [mob(1, HELL_BOVINE, 1.5, 0.0)], [], [])
    open_hand, shield = Mobs(scene, random.Random(3)), Mobs(scene, random.Random(3))
    shield.block_chance = 1.0
    taken = [sum(mobs.tick(HERE, (), scene.hero.sets[0].resist) for _ in range(125)) for mobs in (open_hand, shield)]
    assert taken[0] > 0.0
    assert taken[1] == 0.0
    assert (open_hand.blocked, shield.blocked) == (0, shield.blocked)
    assert shield.blocked > 0

    arena = Arena(strong(one_in_the_open()))

    def blocked(*given) -> float:
        arena.mobs.blocked += 1
        blows(arena)
        return 0.0

    arena.mobs.tick = blocked  # type: ignore[method-assign]
    frames(arena, 1)
    assert mode(arena) == BLOCKING
    frames(arena, round(BLOCK_SECONDS / FRAME) + 2)
    assert mode(arena) != BLOCKING
    assert arena.taken == 0.0


def test_a_buffs_key_pressed_by_a_free_character_is_a_cast_with_its_skill_on_the_button():
    arena = Arena(strong(one_in_the_open()))
    stand = arena.world.player
    assert stand is not None
    home = stand.right_skill
    tap(arena, KEYS[PSYCHIC_WARD])
    stand = arena.world.player
    assert stand is not None
    assert (stand.mode, stand.right_skill) == (CASTING, PSYCHIC_WARD)
    assert arena.acting_until == pytest.approx(QUICK_CAST_SECONDS)
    frames(arena, round(QUICK_CAST_SECONDS / FRAME) + 2)
    stand = arena.world.player
    assert stand is not None
    assert stand.mode != CASTING
    assert stand.right_skill == home


def test_the_hover_record_holds_a_monster_before_the_chest_behind_it():
    chest = Prop(900, CHEST, (HERE[0] + 8.0, HERE[1]))
    scene = strong(Scene('a chest', hero(), [mob(1, HELL_BOVINE, 8.0 - LIFT, -LIFT)], [], []))
    scene.things = [chest]
    arena = Arena(scene)
    point_at(arena, (chest.at[0] - LIFT, chest.at[1] - LIFT))
    assert arena.unit_under_pointer() == (MONSTER_UNIT, 1)
    point_at(arena, (HERE[0] - 10.0, HERE[1]))
    assert arena.unit_under_pointer() == (0, 0)


def test_a_click_on_a_chest_walks_the_character_to_it_and_opens_it():
    chest = Prop(900, CHEST, (HERE[0] + 8.0, HERE[1]))
    scene = strong(Scene('a chest', hero(), [mob(1, HELL_BOVINE, -30.0, 0.0)], [], []))
    scene.things = [chest]
    arena = Arena(scene)
    blows(arena)
    point_at(arena, (chest.at[0] - LIFT, chest.at[1] - LIFT))
    assert arena.unit_under_pointer() == (OBJECT_UNIT, 900)
    click(arena)
    assert [thing.mode for thing in arena.run().containers()] == [0]
    frames(arena, 25)
    assert [thing.mode for thing in arena.run().containers()] == [2]
    assert 4.0 < arena.result().moved < 8.0
