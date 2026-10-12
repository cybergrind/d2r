"""The arena (game.py): the fakes' game with time, monsters that strike, a life, potions and a death.

No macro runs here: the inputs are made on the fake connection as the actuator makes them, and the
game is looked at every game frame, as attack mode looks at it during a fight (macros/hunt.py FRAME).
"""

import math
import random
from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import FULL_REJUVENATION, HEALING, NO_OWNER, SUPER_HEALING, Teleport
from inventory_tracking.models import Outcome, PotionType
from tests.inventory_tracking.macros.fakes import KEYS, OTHER_SET, PREBUFF_SET, WINDOW
from tests.inventory_tracking.scenarios.arena.game import OSD, POTIONS, SERVE, Arena
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.scene import Scene
from tests.inventory_tracking.scenarios.arena.scenes_basic import (
    BELT,
    EMPTY_BELT,
    GLOAM,
    HELL_BOVINE,
    HERE,
    HUNT_SLOTS,
    LIFE,
    STAFF,
    archer_behind_a_wall,
    gloams,
    hero,
    mob,
    one_in_the_open,
    pack_at_low_life,
    potion_on_the_ground,
)


FRAME = 1 / GAME_RATE
VIEW = Viewport(WINDOW[2] / WINDOW[3])
RIGHT_BUTTON = 3  # the X11 button fakes.Game takes for a strike on the right mouse button
SUPER = POTIONS[SUPER_HEALING]


def point_at(arena: Arena, at: tuple[float, float]) -> None:
    """The pointer on the ground at world point `at`."""
    across, down = VIEW.ground(arena.here, *at)
    arena.keys.at = (WINDOW[0] + round(across * WINDOW[2]), WINDOW[1] + round(down * WINDOW[3]))


def tap(arena: Arena, key: str) -> None:
    code = arena.keys.keycodes([key.encode()])[0]
    arena.keys.press(code)
    arena.keys.release(code)


def click(arena: Arena) -> None:
    arena.keys.button(1, True)
    arena.keys.button(1, False)


def frames(arena: Arena, count: int) -> None:
    """`count` game frames with a look at the game in each, and nothing else."""
    for _ in range(count):
        arena.read()
        arena.clock.sleep(FRAME)


def place(arena: Arena, unit: int) -> tuple[float, float]:
    found = next(m for m in arena.world.monsters if m.unit_id == unit)
    return (found.x, found.y)


def strong(scene: Scene, life: float = 1e6) -> Scene:
    """The scene with a character no blow of the test kills."""
    return replace(scene, hero=replace(scene.hero, life=life, max_life=life))


# --- the scene set up ---------------------------------------------------------------------------------


def test_the_scene_is_the_games_start():
    scene = one_in_the_open()
    scene.hero = hero(900.0, hand=1)
    arena = Arena(scene)
    stand = arena.world.player
    assert (stand.name, stand.area, (stand.x, stand.y)) == (scene.hero.name, scene.hero.area, HERE)
    assert arena.world.in_game
    assert arena.world.slots == HUNT_SLOTS
    assert stand.right_skill == ECHOING_STRIKE
    assert (stand.consume, stand.hex_purge, stand.ward) == (True, True, True)
    assert (arena.loot.belt, arena.loot.life, arena.loot.max_life) == (BELT, 900, round(LIFE))
    run = arena.run()
    assert run.hands() == OTHER_SET  # the teleport set is in hand
    assert run.teleport() == Teleport(STAFF.teleport_charges, STAFF.teleport_charges, True)
    assert [(m.unit_id, m.txt_id, (m.x, m.y), m.owner) for m in arena.world.monsters] == [
        (1, HELL_BOVINE, (HERE[0] + 12.0, HERE[1]), NO_OWNER)
    ]
    assert arena.world.dead == frozenset()
    assert run.corpses() == ()
    assert run.ground() is None  # open ground: no map


def test_the_scenes_drops_are_what_the_pickup_step_reads():
    scene = potion_on_the_ground()
    scene.drops += [
        replace(scene.drops[0], unit=51, code=POTIONS[FULL_REJUVENATION]['code']),
        replace(scene.drops[0], unit=52, code=POTIONS[605]['code']),  # a greater healing potion: not read at all
        replace(scene.drops[0], unit=53, code='r24'),
        replace(scene.drops[0], unit=54, code='gld', gold=7200),
    ]
    drops = Arena(scene).run().loot().drops
    assert [(d.unit_id, d.kind, d.label) for d in drops] == [
        (50, HEALING, 'a super healing potion'),
        (51, 'rejuvenation', 'a full rejuvenation potion'),
        (53, 'valuable', 'r24'),
        (54, 'gold', '7200 gold'),
    ]
    assert (drops[0].x, drops[0].y) == scene.drops[0].at


def test_the_scene_given_is_left_as_it_was():
    scene = pack_at_low_life()
    before = scene.copy()
    arena = Arena(scene)
    arena.clock.sleep(5.0)
    assert scene == before


# --- time ---------------------------------------------------------------------------------------------


def test_a_sleep_plays_whole_ticks_and_keeps_the_rest():
    arena = Arena(one_in_the_open())
    for _ in range(3):
        arena.clock.sleep(0.01)
    assert (arena.time.ticks, arena.mobs.frame) == (0, 0)
    arena.clock.sleep(0.01)  # 0.04 s in all: the first tick
    assert (arena.time.ticks, arena.mobs.frame) == (1, 1)
    arena.clock.sleep(1.0)
    assert arena.time.ticks == 26
    assert arena.clock.now == pytest.approx(1.04)
    for _ in range(100):
        arena.clock.sleep(0.013)
    assert arena.time.ticks == round(2.34 * GAME_RATE)  # no time lost in a hundred uneven sleeps


def test_the_monsters_move_as_the_clock_does_and_the_world_shows_them():
    arena = Arena(one_in_the_open())
    start = place(arena, 1)
    arena.clock.sleep(1.0)
    assert math.dist(place(arena, 1), HERE) < math.dist(start, HERE)
    assert place(arena, 1) == arena.mobs.mobs[1].at


# --- the blows on the character ---------------------------------------------------------------------------


def test_a_monster_in_contact_takes_life_at_the_rate_mobs_gives():
    scene = Scene('contact', hero(), [mob(1, HELL_BOVINE, 1.5, 0.0)], [], [])
    arena = Arena(scene, seed=3)
    arena.clock.sleep(5.0)
    bare = Mobs(scene, random.Random(3))
    expected = sum(bare.tick(HERE, (), scene.hero.sets[0].resist) for _ in range(125))
    assert 0.0 < expected < LIFE
    assert arena.taken == pytest.approx(expected)
    assert arena.life == pytest.approx(LIFE - expected)
    assert arena.run().loot().life == round(LIFE - expected)
    assert arena.result().taken == pytest.approx(expected)


def test_the_weapon_set_in_hand_decides_what_an_elemental_attacker_takes():
    staff, main = Arena(strong(gloams())), Arena(strong(gloams()))  # both begin with the teleport set in hand
    tap(main, KEYS[SWAP_WEAPONS])
    assert main.run().hands() == PREBUFF_SET
    for arena in (staff, main):
        arena.clock.sleep(10.0)
    assert staff.taken > 0.0
    # a Gloam's shot is all lightning: 0.92 of it comes through the teleport set, a quarter through the main one
    assert main.taken == pytest.approx(staff.taken * 0.25 / 0.92)
    assert (staff.result().swaps, main.result().swaps) == (0, 1)


# --- the strike -----------------------------------------------------------------------------------------


def test_a_held_strike_kills_one_monster_in_the_open():
    arena = Arena(strong(one_in_the_open()))
    arena.keys.button(RIGHT_BUTTON, True)
    full = arena.world.monsters[0].max_life
    seen = []
    for _ in range(round(20 * GAME_RATE)):
        if not arena.world.monsters:
            break
        point_at(arena, place(arena, 1))
        seen.append(arena.world.monsters[0].life)
        frames(arena, 1)
    arena.keys.button(RIGHT_BUTTON, False)
    result = arena.result()
    assert result.kills == [1]
    assert result.cleared_at is not None
    assert result.cleared_at < 10.0
    # damage.json: 1700 points a contact, a blade once out and once back, the cast's other blades a tenth
    assert result.casts >= full / (1700 * 2 * 1.4)
    assert min(seen) < full  # the life the macro reads went down on the way
    assert arena.world.monsters == ()
    assert arena.world.dead == {1}
    assert [corpse[0] for corpse in arena.run().corpses()] == [1]
    assert [unit for unit, _ in arena.strikes] == [1] * result.casts  # the fakes' record of each cast is kept


def test_the_cast_cadence_is_the_fakes():
    arena = Arena(strong(one_in_the_open()))
    arena.keys.button(RIGHT_BUTTON, True)
    point_at(arena, place(arena, 1))
    frames(arena, 100)
    # 0.3 s of cast (fakes ACTING_SECONDS), a free frame, the next: 0.36 s a cast when looked at every frame
    assert arena.casts == pytest.approx(4.0 / 0.36, abs=1)


def test_nothing_is_cast_with_no_input_held():
    arena = Arena(one_in_the_open())
    point_at(arena, place(arena, 1))
    frames(arena, 100)
    assert arena.casts == 0
    assert arena.world.monsters[0].life == arena.world.monsters[0].max_life


def test_a_wall_stops_the_blades_and_a_hop_into_it():
    scene = strong(archer_behind_a_wall())
    scene.hero.hand = 1  # the staff in hand: a hop needs it
    arena = Arena(scene)
    arena.mobs.pack.walkers[1].traits = replace(arena.mobs.pack.walkers[1].traits, speed=0.0)  # it stays behind
    arena.keys.button(RIGHT_BUTTON, True)
    point_at(arena, place(arena, 1))
    frames(arena, 100)
    arena.keys.button(RIGHT_BUTTON, False)
    assert arena.casts > 5
    assert arena.world.monsters[0].life == arena.world.monsters[0].max_life
    frames(arena, 10)  # the last cast ends
    point_at(arena, (HERE[0] + 7.5, HERE[1] - 5.0))  # in the wall
    tap(arena, KEYS[TELEPORT])
    assert arena.here == HERE
    assert len(arena.refused) == 1
    assert arena.result().charges == 0
    point_at(arena, (HERE[0] + 10.5, HERE[1] - 4.5))  # beyond it
    tap(arena, KEYS[TELEPORT])
    assert arena.here == (HERE[0] + 10.5, HERE[1] - 4.5)  # a sub-tile's centre
    assert arena.result().charges == 1
    assert arena.result().moved == pytest.approx(math.dist(HERE, arena.here))


def test_a_walk_goes_only_where_a_way_leads():
    scene = archer_behind_a_wall()
    scene.mobs = []
    arena = Arena(scene)
    point_at(arena, (HERE[0] + 7.5, HERE[1] - 5.0))  # in the wall
    click(arena)
    assert arena.here == HERE
    point_at(arena, (HERE[0] + 10.0, HERE[1] - 5.0))  # beyond it: the way round its end
    click(arena)
    assert arena.here != HERE
    shut = scene.copy()
    shut.ground = [dict(shut.ground[0])]
    arena = Arena(shut)
    arena.barred = lambda point: point[0] >= HERE[0] + 7.0 and point[0] < HERE[0] + 8.0  # a wall from edge to edge
    point_at(arena, (HERE[0] + 10.0, HERE[1] - 5.0))
    click(arena)
    assert arena.here == HERE


# --- potions --------------------------------------------------------------------------------------------


def test_a_rejuvenation_heals_at_once_and_its_column_comes_down():
    arena = Arena(replace(one_in_the_open(), hero=hero(300.0), mobs=[]))
    tap(arena, '3')
    assert arena.life == LIFE  # potions.json: a full rejuvenation gives 100% of the most life
    assert arena.run().loot().life == round(LIFE)
    assert arena.result().potions == [(0.0, FULL_REJUVENATION, SERVE)]
    assert arena.loot.belt == (*BELT[:14], None, BELT[15])  # one fewer in the column, the hotkey row still full


def test_a_healing_potion_heals_over_its_frames():
    arena = Arena(replace(one_in_the_open(), hero=hero(300.0), mobs=[]), healing_scale=2.0)
    tap(arena, '1')
    assert arena.life == 300.0
    points, length = SUPER['points'] * 2.0, SUPER['frames']
    arena.clock.sleep(length / 2 / GAME_RATE)
    assert arena.life == pytest.approx(300.0 + points / 2)
    arena.clock.sleep(length / 2 / GAME_RATE)
    assert arena.life == pytest.approx(300.0 + points)
    arena.clock.sleep(5.0)
    assert arena.life == pytest.approx(300.0 + points)
    assert arena.result().potions == [(0.0, SUPER_HEALING, SERVE)]


def test_an_empty_cell_gives_nothing():
    arena = Arena(replace(one_in_the_open(), hero=hero(300.0, belt=EMPTY_BELT), mobs=[]))
    tap(arena, '3')
    assert (arena.life, arena.result().potions) == (300.0, [])


def test_a_potion_picked_up_lands_in_the_belt():
    arena = Arena(potion_on_the_ground())
    arena.pick_above = 0.0  # the fakes' game takes the click a little above the drop: here on its ground
    point_at(arena, arena.scene.drops[0].at)
    click(arena)
    assert arena.picked == ['a super healing potion']
    assert arena.loot.drops == ()
    assert arena.loot.belt == BELT
    assert arena.here == arena.scene.drops[0].at
    assert arena.result().moved == pytest.approx(math.dist(HERE, arena.scene.drops[0].at))


# --- the healer beside the macro --------------------------------------------------------------------------


def test_under_forty_percent_the_healer_drinks_a_rejuvenation_with_no_macro():
    arena = Arena(replace(one_in_the_open(), hero=hero(0.39 * LIFE), mobs=[]), osd=PLAYER_HEALING)
    arena.clock.sleep(FRAME)
    assert arena.result().potions == [(FRAME, FULL_REJUVENATION, OSD)]
    assert arena.life == LIFE
    arena.clock.sleep(10.0)
    assert len(arena.result().potions) == 1


def test_under_sixty_five_percent_the_healer_drinks_healing_potions_by_its_cooldown():
    arena = Arena(replace(one_in_the_open(), hero=hero(0.45 * LIFE), mobs=[]), osd=PLAYER_HEALING)
    arena.clock.sleep(7.0)
    drunk = arena.result().potions
    # 320 points over 10.24 s each do not bring 810 of 1800 over 65% in 6 s: one every 3 s (config.PLAYER_HEALING)
    assert [(kind, who) for _, kind, who in drunk] == [(SUPER_HEALING, OSD)] * 3
    gaps = [later[0] - earlier[0] for earlier, later in pairwise(drunk)]
    assert gaps == pytest.approx([PLAYER_HEALING.cooldowns[PotionType.HEALING]] * 2, abs=FRAME)


def test_the_healer_does_nothing_above_its_thresholds_or_without_stock():
    healthy = Arena(replace(one_in_the_open(), hero=hero(0.9 * LIFE), mobs=[]), osd=PLAYER_HEALING)
    bare = Arena(replace(one_in_the_open(), hero=hero(0.3 * LIFE, belt=EMPTY_BELT), mobs=[]), osd=PLAYER_HEALING)
    for arena in (healthy, bare):
        arena.clock.sleep(2.0)
        assert arena.result().potions == []
    assert set(healthy.healer.outcomes) == {Outcome.IDLE}
    assert set(bare.healer.outcomes) == {Outcome.NO_STOCK}


def test_the_healer_sends_nothing_while_a_key_is_down():
    """input/facade.py refuses a potion key while any key is held: a strike held on its key is one."""
    arena = Arena(replace(one_in_the_open(), hero=hero(0.3 * LIFE), mobs=[]), osd=PLAYER_HEALING)
    code = arena.keys.keycodes([KEYS[ECHOING_STRIKE].encode()])[0]
    arena.keys.press(code)
    arena.clock.sleep(3.0)
    assert arena.result().potions == []
    assert Outcome.REJECTED in arena.healer.outcomes
    arena.keys.release(code)
    arena.clock.sleep(1.5)  # the refused try took the cooldown with it
    assert [(kind, who) for _, kind, who in arena.result().potions] == [(FULL_REJUVENATION, OSD)]


def test_the_healer_drinks_under_a_strike_held_on_the_mouse_button():
    arena = Arena(replace(one_in_the_open(), hero=hero(0.3 * LIFE), mobs=[]), osd=PLAYER_HEALING)
    arena.keys.button(RIGHT_BUTTON, True)
    arena.clock.sleep(FRAME)
    assert len(arena.result().potions) == 1


# --- death ----------------------------------------------------------------------------------------------


def test_at_life_zero_the_character_lies_dead_and_nothing_more_is_taken():
    scene = pack_at_low_life()
    arena = Arena(scene)
    arena.clock.sleep(20.0)
    result = arena.result()
    assert result.dead_at is not None
    assert not result.alive
    assert result.dead_at < 5.0
    assert result.seconds == result.dead_at
    assert result.taken == pytest.approx(scene.hero.life)  # all it had and no more
    assert arena.world.player.mode in DEAD
    assert arena.run().loot().life == 0
    assert arena.mobs.frame == round(result.dead_at * GAME_RATE)  # the monsters stood still from then
    arena.keys.button(RIGHT_BUTTON, True)
    frames(arena, 30)
    tap(arena, KEYS[SWAP_WEAPONS])
    assert arena.world.player.mode in DEAD  # no cast ends into a standing character
    assert (arena.casts, arena.swaps) == (0, 0)
    assert arena.result() == result


def test_the_dead_are_not_healed():
    scene = pack_at_low_life()
    scene.hero = hero(LIFE / 6)  # a full belt
    arena = Arena(scene, osd=PLAYER_HEALING)
    arena.mobs.tick = lambda *args: 1e9  # one blow takes it all
    arena.clock.sleep(2.0)
    assert arena.result().dead_at == FRAME
    assert arena.result().potions == []
    tap(arena, '3')
    assert arena.life == 0.0


# --- the result -----------------------------------------------------------------------------------------


def test_the_world_stands_still_after_the_end():
    arena = Arena(strong(pack_at_low_life()))
    arena.clock.sleep(2.0)
    arena.end()
    result = arena.result()
    assert result.seconds == pytest.approx(2.0)
    arena.clock.sleep(3.0)
    arena.say('too late')
    assert arena.result() == result


def test_what_the_macro_says_is_kept_with_its_time():
    arena = Arena(one_in_the_open())
    arena.clock.sleep(1.5)
    arena.run().say('Attack mode on')
    assert arena.result().said == [(1.5, 'Attack mode on')]


def test_a_scene_with_nothing_to_kill_is_cleared_from_the_start():
    assert Arena(potion_on_the_ground()).result().cleared_at == 0.0
    assert Arena(one_in_the_open()).result().cleared_at is None


def scripted(seed: int):
    """A play by a fixed script of inputs: a held strike at the nearest monster, a swap, a potion."""
    scene = gloams()
    scene.mobs += [mob(3, HELL_BOVINE, -6.0, 2.0), mob(4, HELL_BOVINE, 3.0, -7.0)]
    arena = Arena(strong(scene, 4000.0), seed=seed, osd=PLAYER_HEALING)
    arena.keys.button(RIGHT_BUTTON, True)
    for frame in range(round(8 * GAME_RATE)):
        if frame == 20:
            arena.keys.button(RIGHT_BUTTON, False)
            tap(arena, KEYS[SWAP_WEAPONS])
            tap(arena, '1')
            arena.keys.button(RIGHT_BUTTON, True)
        if arena.world.monsters:
            nearest = min(arena.world.monsters, key=lambda m: math.dist(arena.here, (m.x, m.y)))
            point_at(arena, (nearest.x, nearest.y))
        frames(arena, 1)
    return arena.result()


def test_one_seed_and_the_same_inputs_end_equal():
    first, second = scripted(1), scripted(1)
    assert first == second
    assert first.casts > 0
    assert first.taken > 0.0
    assert first.swaps == 1
    assert first.potions[0] == (pytest.approx(20 * FRAME), SUPER_HEALING, SERVE)
    assert scripted(2) != first  # other rolls, another fight


def test_the_basic_scenes_hold_what_they_say():
    assert [m.txt for m in gloams().mobs] == [GLOAM, GLOAM]
    assert gloams().hero.hand == 1
    assert len(pack_at_low_life().mobs) == 8
    assert pack_at_low_life().hero.belt == EMPTY_BELT
