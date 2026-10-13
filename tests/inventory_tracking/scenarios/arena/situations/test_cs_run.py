"""The whole Chaos Sanctuary run as a situation (cs_run.py; rca/2026-10-13/cs-run.md has the plays' table).

Three kinds of test:

- the fixture and the stage's additions (the client's sight, a potion from a kill, Diablo after the fifth seal,
  the stall's end, the tracker's memory), each without a play of the macro;
- **what today's code comes to** (seed 3, the catalog's): plain asserts that pin the state of 2026-10-13 and are
  to be moved when the code moves, each said so where it stands;
- the requirement (user, 2026-10-13: "one press of KP_1, then it runs the whole level automatically") as strict
  expected failures, by today's keys and by the pursuit loop.

Cost: a play that stalls is over in about 3 s of wall time, the two that die in 5 and 10; the one long play
kept here (the recording's own presses by today's keys, to the play's end) takes about 30 s. The package has no
mark for slow tests, so all of them run: about 55 s for the file.
"""

import functools
import math
from dataclasses import replace

import pytest

from inventory_tracking.levels.model import SEALS
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.tracker import HELD_RANGE
from tests.inventory_tracking.scenarios.arena.situations import cs_run
from tests.inventory_tracking.scenarios.arena.situations.catalog import SEED, catalog
from tests.inventory_tracking.scenarios.arena.situations.cs_run import (
    ALONE,
    EMPTY,
    FULL,
    HELD,
    LINGER,
    NAME,
    ONCE,
    RECORDED,
    ROUTE,
    SIGHT,
    STALL,
    LevelStage,
    Memory,
    Run,
    Score,
    cut_run,
    pair,
    played,
    stored,
)
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, load
from tests.inventory_tracking.scenarios.arena.situations.stage import GAME_AWARE, Stage, awareness


SEAL_MARKS = ('Vizier seal 1', 'Vizier seal 2', 'De Seis seal', 'Infector seal 1', 'Infector seal 2')
TODAY, NEW = 0, 1  # the index of a logic in `pair`


@functools.cache
def watched(way: str, staff: str, logic: int, seed: int = SEED) -> tuple[Score, Outcome]:
    """One play of a variant, made once for the tests that read it."""
    label, run, presses = pair(way, staff)[logic]
    found, outcome, _ = played(label, run, presses, seed)
    return found, outcome


def play_of(way: str, staff: str, logic: int, seed: int = SEED) -> Score:
    return watched(way, staff, logic, seed)[0]


def hostiles(run: Run) -> list:
    return [mob for mob in run.scene.mobs if mob.owner is None and not mob.ally]


def staged(run: Run, **given) -> LevelStage:
    potions = {unit: (kind, dx, dy) for unit, kind, dx, dy in run.potions}
    finale = next(unit for unit, name in run.bosses if name == 'Diablo')
    return LevelStage(
        run.scene, seed=1, spawns=run.spawns, aware=run.aware, **{'potions': potions, 'finale': finale, **given}
    )


# -- the fixture ----------------------------------------------------------------------------------------


def test_the_fixture_loads_as_a_run_and_as_a_plain_situation() -> None:
    run = stored()
    assert isinstance(run, Run)
    assert (run.name, run.seconds, run.aware, run.sight) == (NAME, 400.0, GAME_AWARE, SIGHT)
    assert run.source is not None
    assert (run.source['take'], run.source['schema']) == (cs_run.TAKE, 4)
    plain = load(FIXTURES / f'{NAME}.json')  # situation.py reads past this file's part of it
    assert len(plain.scene.mobs) == len(run.scene.mobs)
    assert catalog()[NAME].fixture == f'{NAME}.json'


def test_the_scene_is_the_takes_level_with_its_monsters_and_seals() -> None:
    run = stored()
    hero = run.scene.hero
    # the entrance from the River of Flame: the take's first frame
    assert (hero.area, hero.at, hero.life, hero.max_life) == (108, (7800.5, 5599.88), 1338.0, 1783.0)
    assert hero.sets[1].teleport_charges == cs_run.CHARGES
    assert run.notes['recorded_charges'] == 0
    assert (len(run.scene.ground), len(run.scene.rooms)) == (225, 225)  # the whole level file
    # 255 hostiles in the take: 210 asleep on the level's ground, 18 behind the entrance left out, 26 in the
    # three seal packs, Diablo
    assert len(hostiles(run)) == 210
    assert len(run.outside) == 18
    assert [len(spawn.mobs) for spawn in run.spawns] == [6, 8, 12, 1]
    assert run.notes['hostiles'] == 210 + 18 + 6 + 8 + 12 + 1 == 255
    assert all(mob.life > 0 and mob.mode == 1 for mob in hostiles(run))
    assert sum(1 for mob in run.scene.mobs if mob.owner is not None or mob.ally) == 3  # the companions of frame 0
    assert [name for _, name in run.bosses] == [
        'Grand Vizier of Chaos',
        'Lord De Seis',
        'Infector of Souls',
        'Diablo',
    ]
    # the six marks of the level's card, and a closed seal with the take's own unit id on each of the five
    assert [mark.label for mark in run.marks] == ['Diablo', *SEAL_MARKS]
    seals = {(prop.at[0], prop.at[1]): prop for prop in run.scene.things if prop.txt in SEALS}
    assert len(seals) == 5
    for mark in run.marks[1:]:
        prop = seals[mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS]
        assert (prop.txt, prop.mode) == (mark.use, 0)


def test_a_seal_pack_comes_after_its_own_seal_and_diablo_after_none_of_them() -> None:
    run = stored()
    classes = {prop.unit: prop.txt for prop in run.scene.things}
    packs = [(classes.get(spawn.after), len(spawn.mobs)) for spawn in run.spawns[:3]]
    # the Vizier's with class 396 (not 395), De Seis's with 394, the Infector's with 392: about a second after
    assert packs == [(396, 6), (394, 8), (392, 12)]
    assert all(spawn.delay == pytest.approx(1.0, abs=0.05) for spawn in run.spawns[:3])
    finale = run.spawns[3]
    assert (finale.at, finale.after, finale.label) == (None, None, cs_run.FINALE)
    assert finale.delay == pytest.approx(15.31)
    assert finale.mobs[0].txt == cs_run.DIABLO


def test_the_potions_are_the_takes_own_each_from_a_monster_of_the_scene() -> None:
    run = stored()
    units = {mob.unit for mob in hostiles(run)} | {mob.unit for spawn in run.spawns for mob in spawn.mobs}
    outside = {mob.unit for mob in run.outside}
    assert len(run.potions) == 17
    assert {kind for _, kind, _, _ in run.potions} == {'healing', 'rejuvenation'}
    assert all(unit in units | outside for unit, *_ in run.potions)
    assert all(math.hypot(dx, dy) <= cs_run.DROP_NEAR for _, _, dx, dy in run.potions)


@pytest.mark.skipif(
    not (TAKES / cs_run.TAKE).exists(), reason='the take is not on this machine (takes are git-ignored)'
)
def test_the_fixture_is_what_the_take_cuts_to(tmp_path) -> None:
    path = tmp_path / 'again.json'
    cs_run.dump_run(cut_run(), path)
    assert path.read_text(encoding='utf-8') == (FIXTURES / f'{NAME}.json').read_text(encoding='utf-8')


# -- the stage's additions --------------------------------------------------------------------------------


def test_the_macro_reads_only_what_is_within_the_clients_sight() -> None:
    run = stored()
    arena = staged(run)
    here = arena.here
    seen = [m for m in arena.world.monsters if not m.ally and m.owner == 0xFFFFFFFF]
    assert seen
    assert all(math.dist((m.x, m.y), here) <= SIGHT for m in seen)
    near = sum(1 for mob in hostiles(run) if math.dist(mob.at, here) <= SIGHT)
    assert len(seen) == near < len(hostiles(run))
    assert len([m for m in arena.world.monsters if m.ally or m.owner != 0xFFFFFFFF]) == 3  # the companions always
    assert arena.run().things() == ()  # no seal is in sight of the entrance
    assert len(Stage(run.scene, seed=1).world.monsters) == 210 + 3  # the plain stage shows the whole level


def test_a_monster_sleeps_until_the_character_is_within_the_games_awareness() -> None:
    run = stored()
    arena = staged(run, stall=None)
    entrance = run.scene.hero.at
    walker = next(
        mob for mob in hostiles(run)
        if mob.txt == 310 and math.dist(mob.at, entrance) > 150.0 and arena.footing((mob.at[0] + 12.0, mob.at[1]))
    )  # fmt: skip
    before = {unit: arena.mobs.mobs[unit].at for unit in arena.mobs.live()}
    with awareness(run.aware):
        arena.clock.sleep(2.0)
        assert arena.mobs.mobs[walker.unit].at == before[walker.unit]  # a Doom Knight 150 units off: asleep
        arena.put((walker.at[0] + 12.0, walker.at[1]))
        arena.clock.sleep(2.0)
    here = arena.here
    moved = {unit for unit, at in before.items() if arena.mobs.mobs[unit].at != at}
    assert walker.unit in moved  # it comes for the character 12 units from it
    assert all(
        min(math.dist(before[unit], here), math.dist(before[unit], entrance)) <= GAME_AWARE + 30.0 for unit in moved
    )
    assert len(moved) < 40


def test_a_kill_leaves_the_potion_the_take_had_by_that_corpse() -> None:
    run = stored()
    arena = staged(run, stall=None)
    unit, kind, dx, dy = next(row for row in run.potions if row[0] in arena.mobs.mobs)
    corpse = arena.mobs.mobs[unit].at
    assert arena.mobs.hit(unit, 10**9)
    arena.kills.append(unit)  # as `Arena.fly` counts a kill of the blades
    arena.clock.sleep(0.04)
    assert [(found, what) for _, found, what in arena.dropped] == [(unit, kind)]
    lying = arena.loot.drops[-1]
    assert lying.kind == kind
    assert math.dist((lying.x, lying.y), corpse) <= math.hypot(dx, dy) + 1.0
    assert arena.footing((lying.x, lying.y))


def test_diablo_appears_after_the_fifth_seal_and_not_after_the_fourth() -> None:
    run = stored()
    arena = staged(run, stall=None)
    seals = [thing.unit_id for thing in arena.things if thing.txt_id in SEALS]
    diablo = run.spawns[3].mobs[0].unit
    for unit in seals[:4]:
        arena.operate(unit)
    arena.clock.sleep(20.0)
    assert diablo not in arena.mobs.mobs
    assert [label for _, label, _ in arena.appeared] == [spawn.label for spawn in run.spawns[:3]]
    opened = arena.clock.now
    arena.operate(seals[4])
    arena.clock.sleep(run.spawns[3].delay - 0.5)
    assert diablo not in arena.mobs.mobs
    arena.clock.sleep(1.0)
    assert diablo in arena.mobs.mobs
    assert arena.appeared[-1][0] == pytest.approx(opened + run.spawns[3].delay, abs=0.1)
    # the play ends LINGER seconds after his death
    assert arena.mobs.hit(diablo, 10**9)
    arena.kills.append(diablo)
    fell = arena.clock.now
    arena.clock.sleep(LINGER + 2.0)
    assert arena.over == pytest.approx(fell + LINGER, abs=0.1)
    assert arena.stalled_at is None


def test_a_play_in_which_nothing_happens_is_over_after_the_stall() -> None:
    arena = staged(stored())
    arena.clock.sleep(STALL + 5.0)
    assert arena.stalled_at == pytest.approx(STALL, abs=0.1)
    assert arena.over == arena.stalled_at
    still = staged(stored(), stall=None)
    still.clock.sleep(STALL + 5.0)
    assert still.over is None


def test_the_memory_is_the_trackers_explored_rooms_and_monsters_last_seen() -> None:
    run = stored()
    memory = Memory(108, run.scene.rooms)
    arena = staged(run)
    here = run.scene.hero.at
    seen = [m for m in arena.world.monsters if not m.ally and m.owner == 0xFFFFFFFF]
    memory.note((here[0], here[1] - 1.0), seen, ())
    rooms = memory.explored(108)
    # the character's room and those touching it, as terror/tracker.py `explore` marks them
    assert 2 <= len(rooms) <= 9
    assert memory.explored(107) == set()
    assert {unit for unit, *_ in memory.remembered(108)} == {m.unit_id for m in seen}
    near = min(seen, key=lambda m: math.dist((m.x, m.y), here))
    far = replace(near, unit_id=77, x=near.x, y=near.y - 30.0)  # seen once 50 units off
    assert math.dist((far.x, far.y), here) > HELD_RANGE > math.dist((near.x, near.y), here)
    memory.note(here, [*seen, far], ())
    memory.note(here, [m for m in seen if m.unit_id != near.unit_id], ())
    left = {unit for unit, *_ in memory.remembered(108)}
    assert far.unit_id in left  # out of sight further than the client holds a monster: remembered where it was
    assert near.unit_id not in left  # not there where the client would hold it: it moved or died unseen
    memory.note(here, [replace(far, mode=12)], ())
    assert far.unit_id not in {unit for unit, *_ in memory.remembered(108)}


# -- the plays: what today's code comes to (seed 3; pins of 2026-10-13, to be moved with the code) --------------


def test_a_play_is_the_same_play_for_a_seed() -> None:
    label, run, presses = pair(ONCE, FULL)[TODAY]
    first, one = watched(ONCE, FULL, TODAY)
    second, two, _ = played(label, run, presses, seed=SEED)
    assert (one.track, one.kills, one.said, one.life) == (two.track, two.kills, two.said, two.life)
    assert replace(first, wall=0.0) == replace(second, wall=0.0)


def test_today_one_press_of_the_pickup_key_fights_what_is_near_and_stands() -> None:
    """Pins today's state (the pursuit off): KP_1 turns attack mode on with its sweep, the sweep takes one step to
    the pack by the entrance, the fight there ends with "Nothing left in reach" and nothing follows: no hostile is
    within the sweep's 60 units, no route stage is the pickup key's. The play is ended as a stall. With the
    pursuit on the same press is a level run (the requirement below, rca/2026-10-13/kp1-level-run.md)."""
    found = play_of(ONCE, FULL, TODAY)
    assert found.ended == 'stalled'
    assert found.seconds < STALL + 10.0
    assert (found.stage, found.stages_done) == (ROUTE[0], 0)
    assert all(at is None for at in found.seals.values())
    assert 1 <= found.kills <= 4
    assert found.attack_mode  # the mode is still on: it waits where it stands
    assert found.nearest is not None
    assert found.nearest[1] > 60.0  # hunt.py SWEEP_UNITS
    assert found.moved < 40.0
    assert found.dead_at is None


def test_today_attack_mode_alone_never_leaves_the_entrance() -> None:
    """Pins today's state: the mode goes nowhere. Since the casters think by the client's code (sim/casters.py,
    2026-10-13: awake within 35, after the nearest body) the entrance's two Storm Casters come into the strike's
    reach and die (before: 0 kills, 0 strikes, nothing came)."""
    found = play_of(ALONE, FULL, TODAY)
    assert (found.ended, found.kills, found.strikes, found.moved) == ('stalled', 2, 8, 0.0)
    assert found.stage == ROUTE[0]


def test_today_the_pickup_key_and_a_held_teleport_key_open_the_viziers_seals_and_die_without_a_strike() -> None:
    """Pins today's state: with the staff full the held teleport key takes the route to the Vizier's two seals,
    and no strike is ever cast: each press pauses attack mode and the quiet after it (runner.py TRAVEL_QUIET; the
    strict expected failure of test_incident_kp4.py, here for a whole level). The pack kills the character."""
    found = play_of(HELD, FULL, TODAY)
    assert found.ended == 'dead'
    assert found.strikes == 0
    assert found.kills == 0
    assert found.seals['Vizier seal 1'] is not None
    assert found.seals['De Seis seal'] is None
    assert found.bosses['Grand Vizier of Chaos'] is None
    assert found.stages_done <= 2
    assert found.charges > 5


def test_today_with_the_staff_empty_the_held_teleport_key_stalls_by_the_star_short_of_the_first_seal() -> None:
    """Pins today's state: no strike and no seal. Since the Blade Warp's delay is read from the game
    (macros/travel.py `delay_over`, 2026-10-14) the step finds its warps: 13 of them take the character about
    300 units north to 35 units from the star, where the step stops on "no Blade Warp or walk leads toward
    Vizier seal 1" (hunt.py) 115 units short of it, and nothing more happens: the play ends as a stall, alive
    (before: the step stopped on that line in the entrance's hall and the packs killed the character there).
    Over ten seeds: six stall so (four by the star), one dies on the way, three open Vizier seal 1 and die by
    the second; none strikes or comes to Vizier seal 2."""
    found, outcome = watched(HELD, EMPTY, TODAY)
    assert (found.ended, found.strikes, found.kills, found.stages_done, found.charges) == ('stalled', 0, 0, 0, 0)
    assert found.dead_at is None
    assert all(at is None for at in found.seals.values())
    assert outcome.said_count('Blade Warp toward Vizier seal 1') >= 10
    assert outcome.said_count('no Blade Warp or walk leads toward Vizier seal 1') > 10
    assert found.last_move is not None
    assert found.last_move < found.seconds - STALL + 1.0  # it stood from there to the stall's end
    assert found.near[0] == 'Diablo'  # the nearest mark: the star
    assert found.near[1] < 40.0
    seal = next(mark for mark in stored().marks if mark.label == 'Vizier seal 1')
    assert math.dist(found.end, (seal.spot[0] * TILE_UNITS, seal.spot[1] * TILE_UNITS)) > 100.0


def test_today_the_recordings_own_presses_with_the_staff_empty_take_the_route_part_of_the_way() -> None:
    """The one long play (about 30 s of wall time). Pins today's state: the 251 presses of the real game (187
    of the teleport key, 64 of the pickup key) played by today's keys open seals and kill a seal boss, do not
    die, and do not come to Diablo before they run out at 252 s."""
    found = play_of(RECORDED, EMPTY, TODAY)
    assert found.dead_at is None
    assert found.seals['Vizier seal 1'] is not None
    assert found.kills > 100
    assert 1 <= found.stages_done < len(ROUTE)
    assert not found.done


@pytest.mark.xfail(strict=True, reason='one press of the pickup key is one fight: nothing takes the route on (KP_1)')
def test_one_press_of_the_pickup_key_clears_the_level_and_kills_diablo() -> None:
    found = play_of(ONCE, FULL, TODAY)
    assert found.done
    assert found.dead_at is None


def test_one_press_of_the_pickup_key_clears_the_level_by_the_pursuit_loop() -> None:
    """The requirement, by the pursuit loop (rca/2026-10-13/kp1-level-run.md): the pickup key's press is a level run
    (macros/pursuit.py, the leash), which works every stage of the route in order with no other press: the five
    seals, the three seal bosses and Diablo; drops on the way; alive at the end."""
    found = play_of(ONCE, FULL, NEW)
    assert found.done
    assert found.dead_at is None
    assert found.stages_done == len(ROUTE)
    assert all(at is not None for at in found.seals.values())
    assert found.picked > 0


def test_the_level_run_waits_out_what_a_seal_brings_and_fights_it_before_the_next_seal() -> None:
    """The stop of rca/2026-10-13/cs-run.md §5 item 6 under the level run: the run does not hop into the pack a
    seal brings (the Infector's twelve stand on the next seal): the seal's dwell is waited out and what stands by
    the next seal is fought first (macros/goals.py `first_fight`, `in_the_way`), and the boss dies before it."""
    found = play_of(ONCE, FULL, NEW)
    assert found.dead_at is None
    assert found.bosses['Infector of Souls'] is not None
    assert found.bosses['Infector of Souls'] < found.seals['Infector seal 2']  # its pack before the last seal
