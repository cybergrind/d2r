"""The arena's monsters (mobs.py): sim.monsters on walled ground, with ranged attackers, blasts and auras."""

import math
import random
from dataclasses import asdict

import pytest

from inventory_tracking.combat.sim.monsters import (
    COLD,
    REACH,
    UNIQUE_FLAG,
    Pack,
    Traits,
    Walker,
    nova_points,
    shooter_of,
)
from inventory_tracking.game.layout import LYING_DEAD, NO_OWNER
from inventory_tracking.levels.model import Walkable, pack_cells
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.arena.evidence.sure import sure
from tests.inventory_tracking.scenarios.arena.mobs import (
    AURA_FACTOR,
    AURA_MOD,
    AURA_RANGE,
    BLAST,
    BLAST_KIND,
    BLAST_RADIUS,
    RANGED_REACH,
    SHOT_FRAMES,
    Mobs,
    is_ranged,
    shooter,
    shot_parts,
)
from tests.inventory_tracking.scenarios.arena.scene import Hero, Mob, Scene, WeaponSet


# txt ids, each a row of threat_table.json (scenarios/threat/scenes.py names the same ones)
GHOUL, HELL_BOVINE = 7, 391  # melee, neither character-first nor holding off (sim.monsters CHARACTER_FIRST, HOLD)
RETURNED_ARCHER, GLOAM = 578, 118  # ranged by the threat table; the Gloam is melee by monstats
UNDEAD_SOUL_KILLER = 691  # its corpse explodes
VENOM_LORD = 362  # not ranged by the table, not melee by monstats
HERE = (5020.0, 5020.0)
OPEN: dict[str, float] = {}  # every kind of damage let through
SIDE = 8  # tiles of the walled ground's side, from tile (1000, 1000): world 5000 to 5040


@pytest.fixture(autouse=True)
def every_blow_lands(monkeypatch):
    """This file is of walls, lines of sight, blasts and auras: every swing and shot lands in it (the
    fitted chances that they do are tests/inventory_tracking/combat/test_monsters.py's)."""
    sure(monkeypatch)


def scene(mobs: list[Mob], ground: list[dict] | None = None, doors: list[list] | None = None) -> Scene:
    hand = WeaponSet((), {})
    hero = Hero('test', HERE, 1, 1800.0, 1800.0, 100.0, 100.0, (None,) * 16, (hand, hand))
    return Scene('test', hero, mobs, ground or [], doors or [])


def mob(unit: int, txt: int, dx: float, dy: float, **more) -> Mob:
    """A monster `dx`, `dy` units from the character, with 1000 points of life."""
    return Mob(unit, txt, (HERE[0] + dx, HERE[1] + dy), more.pop('level', 85), 1000.0, 1000.0, **more)


def walled(barred) -> list[dict]:
    """A square of ground whose unit cells `barred(x, y)` (units from its corner) are walls, to walk and to fly."""
    units = SIDE * TILE_UNITS
    cells = pack_cells(''.join('0' if barred(x, y) else '1' for y in range(units) for x in range(units)))
    return [asdict(Walkable(1000, 1000, SIDE, SIDE, cells, cells))]


def played(mobs: Mobs, ticks: int, hero: tuple[float, float] = HERE, companions=(), resist=OPEN) -> float:
    return sum(mobs.tick(hero, companions, resist) for _ in range(ticks))


def place(mobs: Mobs, unit: int) -> tuple[float, float]:
    found = next(m for m in mobs.monsters() if m.unit_id == unit)
    return (found.x, found.y)


# --- what sim.monsters does already, kept ---------------------------------------------------------------


def test_open_ground_keeps_the_packs_own_walk_roll_for_roll():
    seed = 5
    mobs = Mobs(scene([mob(1, GHOUL, 12.0, 3.0), mob(2, HELL_BOVINE, -9.0, 8.0)]), random.Random(seed))
    walkers = [
        Walker(1, GHOUL, HERE[0] + 12.0, HERE[1] + 3.0, level=85),
        Walker(2, HELL_BOVINE, HERE[0] - 9.0, HERE[1] + 8.0, level=85),
    ]
    pack = Pack(walkers, random.Random(seed).getrandbits(32))
    for frame in range(300):
        taken = mobs.tick(HERE, (), OPEN)
        blows = pack.step(frame, [HERE])
        assert taken == pytest.approx(sum(blow.damage for blow in blows))
        assert place(mobs, 1) == pack.walkers[1].at
        assert place(mobs, 2) == pack.walkers[2].at
    assert math.dist(place(mobs, 2), HERE) <= REACH  # the cow got there; the Ghoul makes 1.1 units a second


def test_a_melee_monster_walks_in_and_takes_life():
    mobs = Mobs(scene([mob(1, HELL_BOVINE, 10.0, 0.0)]), random.Random(1))
    assert played(mobs, 50) == 0.0  # still on its way: 10 units at 5.5 a second
    assert played(mobs, 250) > 0.0
    assert math.dist(place(mobs, 1), HERE) <= REACH


def test_resistance_cuts_each_kind_of_a_blow():
    full = played(Mobs(scene([mob(1, HELL_BOVINE, 2.0, 0.0)]), random.Random(1)), 200)
    halved = played(Mobs(scene([mob(1, HELL_BOVINE, 2.0, 0.0)]), random.Random(1)), 200, resist={'physical': 0.5})
    other = played(Mobs(scene([mob(1, HELL_BOVINE, 2.0, 0.0)]), random.Random(1)), 200, resist={'fire': 0.0})
    assert full > 0.0
    assert halved == pytest.approx(full / 2)
    assert other == pytest.approx(full)  # a kind the blow has none of; the missing kinds let all through


def test_a_type_monstats_does_not_flag_melee_still_fights_hand_to_hand():
    assert not Traits.of(VENOM_LORD).melee
    assert not is_ranged(VENOM_LORD)
    mobs = Mobs(scene([mob(1, VENOM_LORD, 8.0, 0.0)]), random.Random(1))
    assert played(mobs, 300) > 0.0
    assert math.dist(place(mobs, 1), HERE) <= REACH


# --- walls --------------------------------------------------------------------------------------------


def test_a_melee_monster_goes_round_a_wall():
    # a wall across x = 20 from the top edge down to y = 26: the way round is under its end
    ground = walled(lambda x, y: x == 20 and y < 26)
    mobs = Mobs(scene([mob(1, HELL_BOVINE, -8.0, -4.0)], ground), random.Random(1))
    start, taken, crossed = place(mobs, 1), 0.0, []
    for _ in range(600):
        taken += mobs.tick((HERE[0] + 6.0, HERE[1] - 4.0), (), OPEN)
        at = place(mobs, 1)
        crossed.append(at)
        assert not (math.floor(at[0]) == 5020 and at[1] < 5026), 'it stood in the wall'
    assert start[0] < 5020 < crossed[-1][0]
    assert max(at[1] for at in crossed) >= 5026  # it went under the wall's end
    assert taken > 0.0


def test_with_no_way_a_melee_monster_stands():
    ground = walled(lambda x, y: x == 20)  # a wall from edge to edge
    mobs = Mobs(scene([mob(1, HELL_BOVINE, -1.5, 0.0)], ground), random.Random(1))
    start = place(mobs, 1)
    assert played(mobs, 300, (HERE[0] + 6.0, HERE[1])) == 0.0
    assert place(mobs, 1) == start


def test_a_closed_door_bars_the_walk_and_an_open_one_does_not():
    ground = walled(lambda x, y: x == 20 and y != 20)  # a wall with a doorway one unit wide
    hero = (HERE[0] + 8.0, HERE[1] + 0.5)

    def through(mode: int) -> tuple[float, float]:
        """The points taken and how far east the cow got, with the door in the doorway in `mode`."""
        door = [900, 0, mode, 5020.5, 5020.5]  # unit, txt, mode, x, y, as a stance fixture holds a door
        mobs = Mobs(scene([mob(1, HELL_BOVINE, -6.0, 0.5)], ground, [door]), random.Random(1))
        return played(mobs, 300, hero), place(mobs, 1)[0]

    opened, closed = through(2), through(0)  # levels/doors.py CLOSED_MODE 0; 2 is opened
    assert opened[0] > 0.0
    assert opened[1] > 5021
    assert closed[0] == 0.0
    assert closed[1] < 5020


# --- ranged attackers ---------------------------------------------------------------------------------


def test_a_ranged_monster_shoots_from_where_it_stands():
    mobs = Mobs(scene([mob(1, RETURNED_ARCHER, 25.0, 0.0)]), random.Random(1))
    start = place(mobs, 1)
    seconds = 120
    taken = played(mobs, seconds * SHOT_FRAMES)
    walker = mobs.pack.walkers[1]
    assert place(mobs, 1) == start
    # Since the refit of the monsters the rate is the takes' (0.42 shots a second for the type: one
    # every 60 frames, the gap drawn from half to one and a half of that), no longer a shot a second;
    # a shot is still a second of the threat table's points.
    rate = shooter_of(RETURNED_ARCHER)['rate']['value']
    assert rate == pytest.approx(0.416)
    assert taken == pytest.approx(sum(shot_parts(walker).values()) * seconds * rate, rel=0.1)
    assert set(shot_parts(walker)) == {'physical', 'cold'}  # the archer's row: 0.5 physical, 0.8 elemental, cold


def test_a_ranged_monsters_shot_is_cut_by_its_kinds_resistance():
    full = played(Mobs(scene([mob(1, GLOAM, 20.0, 0.0)]), random.Random(1)), 250)
    resisted = played(Mobs(scene([mob(1, GLOAM, 20.0, 0.0)]), random.Random(1)), 250, resist={'lightning': 0.25})
    assert full > 0.0
    assert resisted == pytest.approx(full / 4)  # a Gloam's row is elemental only, lightning


def test_a_ranged_monster_out_of_its_reach_stands_and_deals_nothing():
    mobs = Mobs(scene([mob(1, RETURNED_ARCHER, RANGED_REACH + 5.0, 0.0)]), random.Random(1))
    start = place(mobs, 1)
    assert played(mobs, 250) == 0.0
    assert place(mobs, 1) == start


def test_a_ranged_monster_follows_a_character_that_left_its_reach():
    mobs = Mobs(scene([mob(1, RETURNED_ARCHER, 25.0, 0.0)]), random.Random(1))
    assert played(mobs, 150) > 0.0  # its first shot within a gap and a half, and the arrow's flight
    far = (HERE[0] - 20.0, HERE[1])  # 45 units from it now
    assert played(mobs, 400, far) > 0.0
    assert math.dist(place(mobs, 1), far) <= RANGED_REACH


def test_a_ranged_monster_without_a_line_closes_until_it_has_one():
    ground = walled(lambda x, y: x == 20 and y < 26)
    hero = (HERE[0] + 6.0, HERE[1] - 4.0)
    mobs = Mobs(scene([mob(1, RETURNED_ARCHER, -8.0, -4.0)], ground), random.Random(1))
    start = place(mobs, 1)
    assert played(mobs, 20, hero) == 0.0  # the wall is in the way
    assert played(mobs, 600, hero) > 0.0
    at = place(mobs, 1)
    assert at != start
    assert math.dist(at, hero) > REACH  # it stopped when it had the line, not in contact


def test_a_ranged_monster_walled_off_deals_nothing():
    ground = walled(lambda x, y: x == 20)
    mobs = Mobs(scene([mob(1, RETURNED_ARCHER, -8.0, 0.0)], ground), random.Random(1))
    assert played(mobs, 400, (HERE[0] + 6.0, HERE[1])) == 0.0


def test_rank_raises_a_shot_as_it_raises_a_blow():
    plain = Mobs(scene([mob(1, RETURNED_ARCHER, 25.0, 0.0)]), random.Random(1))
    unique = Mobs(scene([mob(1, RETURNED_ARCHER, 25.0, 0.0, flags=UNIQUE_FLAG)]), random.Random(1))
    shot = played(plain, 250)
    assert shot > 0.0
    assert played(unique, 250) == pytest.approx(shot * 1.66)  # difficultylevels UniqueDamageBonus 66


# --- blasts -------------------------------------------------------------------------------------------


def test_an_exploding_corpse_within_the_radius_deals_its_blast():
    mobs = Mobs(scene([mob(1, UNDEAD_SOUL_KILLER, BLAST_RADIUS - 1.0, 0.0)]), random.Random(1))
    assert mobs.hit(1, 2000.0) is True
    assert mobs.tick(HERE, (), {BLAST_KIND: 0.5}) == pytest.approx(BLAST / 2)
    assert mobs.tick(HERE, (), OPEN) == 0.0  # once


def test_an_exploding_corpse_beyond_the_radius_deals_nothing():
    mobs = Mobs(scene([mob(1, UNDEAD_SOUL_KILLER, BLAST_RADIUS + 1.0, 0.0)]), random.Random(1))
    assert mobs.hit(1, 2000.0) is True
    assert mobs.tick(HERE, (), OPEN) == 0.0


def test_a_corpse_that_does_not_explode_deals_nothing():
    mobs = Mobs(scene([mob(1, GHOUL, 1.0, 0.0)]), random.Random(1))
    assert mobs.hit(1, 2000.0) is True
    assert played(mobs, 50) == 0.0


# --- auras --------------------------------------------------------------------------------------------


def aura_scenes() -> tuple[Scene, Scene, Scene]:
    """A striker beside the character with an Aura Enchanted monster near it; the same with the aura
    taken off; the striker alone. A monster's rolls are its own, so the three differ by the aura only."""
    striker = mob(1, HELL_BOVINE, 2.0, 0.0)
    holder = mob(2, GHOUL, 2.0 + AURA_RANGE - 4.0, 0.0)
    with_aura = scene([striker, mob(2, GHOUL, holder.at[0] - HERE[0], 0.0, mods=(AURA_MOD,))])
    return with_aura, scene([striker, holder]), scene([striker])


def test_an_aura_raises_the_blows_of_the_others_in_its_range():
    with_aura, without, alone = aura_scenes()
    raised = played(Mobs(with_aura, random.Random(3)), 100)
    plain = played(Mobs(without, random.Random(3)), 100)
    striker = played(Mobs(alone, random.Random(3)), 100)
    assert striker > 0.0
    assert raised == pytest.approx(plain + striker * (AURA_FACTOR - 1))  # the holder's own blows are not raised


def test_an_aura_ends_with_its_holder():
    with_aura, _, alone = aura_scenes()
    mobs, plain = Mobs(with_aura, random.Random(3)), Mobs(alone, random.Random(3))
    assert mobs.hit(2, 2000.0) is True
    assert played(mobs, 100) == pytest.approx(played(plain, 100))


def test_a_scene_may_name_its_own_auras_and_one_out_of_range_raises_nothing():
    # the holder is an archer out of its own reach and its aura's: it only stands there
    striker, away = mob(1, HELL_BOVINE, 2.0, 0.0), max(RANGED_REACH, AURA_RANGE) + 5.0
    alone = played(Mobs(scene([striker]), random.Random(3)), 100)
    far = scene([striker, mob(2, RETURNED_ARCHER, 2.0, away)])
    assert played(Mobs(far, random.Random(3), auras={2: 3.0}), 100) == pytest.approx(alone)
    assert played(Mobs(far, random.Random(3), auras={}), 100) == pytest.approx(alone)
    # the same archer with a cow that stands inside its aura, and the character beside the cow
    idle = mob(1, HELL_BOVINE, 2.0, away - AURA_RANGE + 1.0)
    near = scene([idle, mob(2, RETURNED_ARCHER, 2.0, away)])
    hero = (idle.at[0] + 2.0, idle.at[1])  # beside the cow
    lone = played(Mobs(scene([idle]), random.Random(3)), 200, hero)
    both = played(Mobs(near, random.Random(3), auras={}), 200, hero)
    raised = played(Mobs(near, random.Random(3), auras={2: 3.0}), 200, hero)
    assert lone > 0.0
    assert raised == pytest.approx(both + lone * 2.0)  # the cow's blows three times, the archer's shots as they were


# --- companions ---------------------------------------------------------------------------------------


def test_a_monster_goes_for_the_nearest_of_the_character_and_its_companions():
    companion = (HERE[0] + 15.0, HERE[1])
    mobs = Mobs(scene([mob(1, HELL_BOVINE, 17.0, 0.0)]), random.Random(1))
    assert played(mobs, 300, companions=[companion]) == 0.0  # it strikes the companion beside it
    assert math.dist(place(mobs, 1), companion) <= REACH
    assert played(mobs, 300) > 0.0  # the companion gone, it comes for the character


def test_a_companion_of_the_scene_is_no_hostile_and_stands_where_it_is():
    demon = mob(9, GHOUL, 3.0, 0.0, owner=1, ally=True)
    mercenary = mob(8, GHOUL, -3.0, 0.0, ally=True)
    mobs = Mobs(scene([mob(1, HELL_BOVINE, 30.0, 0.0), demon, mercenary]), random.Random(1))
    assert mobs.live() == [1]
    assert played(mobs, 100) == 0.0  # the companions strike nobody, the cow is beyond AWARE
    records = {m.unit_id: m for m in mobs.monsters()}
    assert (records[9].x, records[9].y, records[9].owner, records[9].ally) == (*demon.at, 1, True)
    assert (records[8].owner, records[8].ally) == (NO_OWNER, True)
    assert mobs.hit(9, 5000.0) is False
    assert next(m for m in mobs.monsters() if m.unit_id == 9).life == 1000


# --- hits, records ------------------------------------------------------------------------------------


def test_hit_takes_life_and_says_when_it_died():
    mobs = Mobs(scene([mob(1, GHOUL, 5.0, 0.0), mob(2, GHOUL, 6.0, 1.0)]), random.Random(1))
    assert mobs.hit(1, 400.0) is False
    assert next(m for m in mobs.monsters() if m.unit_id == 1).life == 600
    assert mobs.hit(1, 600.0) is True
    assert mobs.hit(1, 600.0) is False  # a corpse dies once
    assert mobs.hit(77, 600.0) is False
    assert mobs.live() == [2]


def struck_every(points: float, ticks: int = 1000, every: int = 12) -> tuple[float, Mobs]:
    """A cow beside the character, of a million points of life at the most and far more than that left
    (it is not to die here), hit for `points` every `every` ticks: the life it took off the character,
    and the monsters."""
    mobs = Mobs(scene([Mob(1, HELL_BOVINE, (HERE[0] + 2.0, HERE[1]), 85, 1e12, 1e6)]), random.Random(1))
    taken = 0.0
    for tick in range(ticks):
        taken += mobs.tick(HERE, [], OPEN)
        if tick % every == 0:
            mobs.hit(1, points)
    return taken, mobs


def test_a_hit_that_takes_a_good_part_of_its_life_staggers_a_monster_and_its_swing_is_lost(monkeypatch):
    monkeypatch.undo()  # this one test is of the stagger: the file's others have none (`every_blow_lands`)
    sure(monkeypatch, stagger=True)
    # Every swing that runs out lands here (`sure`): what a struck monster deals less is what its staggers cost.
    calm, _mobs = struck_every(0.0)
    grazed, _mobs = struck_every(1e6 / 100)  # a hundredth of its life: under a sixteenth, seldom a stagger
    reeling, mobs = struck_every(1e6 / 4)  # a quarter: nine times in ten
    assert calm > 0
    assert grazed > 0.6 * calm
    assert reeling < 0.4 * calm
    assert mobs.pack.walkers[1].fell == 0.0  # a tick's hits are rolled for at the next tick, once


def test_the_hits_of_one_tick_are_one_fall_of_their_sum():
    mobs = Mobs(scene([mob(1, HELL_BOVINE, 2.0, 0.0)]), random.Random(1))
    mobs.tick(HERE, [], OPEN)
    for _ in range(4):
        mobs.hit(1, 50.0)
    assert mobs.pack.walkers[1].fell == pytest.approx(0.2)  # 200 of its 1000 points


def test_nothing_comes_off_an_immune_monster():
    mobs = Mobs(scene([mob(1, GHOUL, 5.0, 0.0, immune=True)]), random.Random(1))
    assert mobs.hit(1, 5000.0) is False
    assert mobs.live() == [1]
    assert mobs.monsters()[0].life == 1000


def test_the_records_are_the_games_and_the_dead_lie_where_they_fell():
    scened = scene([
        mob(1, GHOUL, 5.0, 0.0, flags=UNIQUE_FLAG, mods=(5, 17), tier=2),
        mob(2, GHOUL, 8.0, 0.0, mode=LYING_DEAD),
    ])  # fmt: skip
    scened.mobs[1].life = 0.0
    mobs = Mobs(scened, random.Random(1))
    assert mobs.live() == [1]
    assert mobs.corpses() == ((2, HERE[0] + 8.0, HERE[1]),)
    played(mobs, 30)
    live = next(m for m in mobs.monsters() if m.unit_id == 1)
    assert (live.txt_id, live.mode, live.owner, live.flags, live.life, live.max_life) == (
        GHOUL,
        1,
        NO_OWNER,
        8,
        1000,
        1000,
    )
    assert (live.modifiers, live.tier, live.leader) == ((5, 17), 2, True)
    fell = (live.x, live.y)
    assert mobs.hit(1, 5000.0) is True
    dead = next(m for m in mobs.monsters() if m.unit_id == 1)
    assert (dead.mode, dead.life, dead.x, dead.y) == (LYING_DEAD, 0, *fell)
    assert mobs.corpses() == ((1, *fell), (2, HERE[0] + 8.0, HERE[1]))
    played(mobs, 30)
    assert mobs.corpses()[0] == (1, *fell)  # a corpse does not walk
    assert mobs.live() == []


def test_the_scene_given_is_not_changed():
    scened = scene([mob(1, HELL_BOVINE, 6.0, 0.0)])
    before = scened.copy()
    mobs = Mobs(scened, random.Random(1))
    played(mobs, 100)
    mobs.hit(1, 300.0)
    assert scened == before


# --- determinism --------------------------------------------------------------------------------------


def busy_scene() -> Scene:
    ground = walled(lambda x, y: x == 20 and y < 12)
    return scene(
        [
            mob(1, HELL_BOVINE, -8.0, -12.0),
            mob(2, GHOUL, 9.0, 4.0, flags=UNIQUE_FLAG, mods=(17, AURA_MOD)),  # Lightning Enchanted: sparks
            mob(3, RETURNED_ARCHER, 14.0, 10.0),
            mob(4, GLOAM, -12.0, 14.0, tier=1),
            mob(5, UNDEAD_SOUL_KILLER, 5.0, -3.0),
            mob(6, VENOM_LORD, 3.0, 12.0, immune=True),
            mob(9, GHOUL, 2.0, 2.0, owner=1, ally=True),
        ],
        ground,
    )


def story(seed: int) -> list:
    """A few hundred ticks of a busy scene: the character walks, strikes what is alive, a companion stands by."""
    mobs = Mobs(busy_scene(), random.Random(seed))
    told: list = []
    for tick in range(400):
        hero = (HERE[0] + 4.0 * math.sin(tick / 40), HERE[1] + tick / 100)
        told.append(mobs.tick(hero, [(hero[0] + 2.0, hero[1] + 2.0)], {'physical': 0.6, 'lightning': 0.25}))
        if tick % 9 == 0:
            told.append([mobs.hit(unit, 45.0) for unit in mobs.live()])
        told.append([(m.unit_id, m.mode, m.x, m.y, m.life) for m in mobs.monsters()])
        told.append(mobs.corpses())
    return told


def test_equal_scenes_and_seeds_give_equal_fights():
    first, second = story(11), story(11)
    assert first == second
    assert sum(entry for entry in first if isinstance(entry, float)) > 0.0
    assert any(entry for entry in first if isinstance(entry, tuple))  # something died on the way


def test_another_seed_gives_another_fight():
    assert story(11) != story(12)


# --- what the refit of the monsters added (2026-10-12) ---------------------------------------------------

CARVER_SHAMAN, DARK_STALKER = 59, 45  # shoot in the takes; the threat table calls neither ranged


def test_a_type_the_takes_show_shooting_is_a_shooter_though_the_threat_table_does_not_call_it_ranged():
    assert not is_ranged(CARVER_SHAMAN)
    assert shooter(CARVER_SHAMAN)
    assert not shooter(DARK_STALKER)  # it strikes too in the takes (30 s in reach): its missiles are an enchantment's
    assert not shooter(GHOUL)
    mobs = Mobs(scene([mob(1, CARVER_SHAMAN, 12.0, 0.0), mob(2, DARK_STALKER, 12.0, 4.0)]), random.Random(1))
    assert set(mobs.pack.shots) == {1}
    assert (mobs.pack.walkers[1].traits.melee, mobs.pack.walkers[2].traits.melee) == (False, True)


def test_a_missile_in_the_air_misses_a_character_that_left_and_hits_one_that_stayed():
    def taken(leaves: bool) -> float:
        mobs = Mobs(scene([mob(1, RETURNED_ARCHER, 24.0, 0.0)]), random.Random(1))
        total = 0.0
        for _tick in range(1500):
            # Away whenever an arrow is in the air, back when none is.
            away = leaves and bool(mobs.pack.flying)
            total += mobs.tick((HERE[0], HERE[1] + 10.0) if away else HERE, (), OPEN)
        return total

    assert taken(False) > 0.0
    assert taken(True) == 0.0


def test_the_death_of_a_cold_enchanted_elite_lets_a_nova_go_that_the_cold_resistance_cuts():
    def nova(resist, **more) -> float:
        mobs = Mobs(scene([mob(1, GHOUL, 9.0, 0.0, mods=(COLD,), **more)]), random.Random(4))
        assert mobs.hit(1, 2000.0) is True
        return played(mobs, 30, resist=resist)

    whole = nova(OPEN, flags=UNIQUE_FLAG)
    assert whole in (nova_points(85), 2 * nova_points(85))  # the missile's points at the monster's level, or twice
    assert nova({'cold': 0.25}, flags=UNIQUE_FLAG) == pytest.approx(whole / 4)
    assert nova(OPEN) == 0.0  # a plain monster carrying Cold Enchanted lets none go (0 of 373 in the takes)


def test_equal_seeds_give_equal_fights_with_shooters_and_novas():
    def fight(seed: int) -> list[float]:
        mobs = Mobs(
            scene([
                mob(1, RETURNED_ARCHER, 20.0, 0.0),
                mob(2, GHOUL, 6.0, 2.0, mods=(COLD,), flags=UNIQUE_FLAG),
                mob(3, HELL_BOVINE, -3.0, 0.0),
            ]),
            random.Random(seed),
        )  # fmt: skip
        told = []
        for tick in range(400):
            if tick == 100:
                mobs.hit(2, 5000.0)
            told.append(mobs.tick(HERE, [(HERE[0] + 3.0, HERE[1] + 3.0)], OPEN))
        return told

    assert fight(7) == fight(7)
    assert fight(7) != fight(8)


def test_a_walker_shows_the_client_s_walk_and_swing_modes_and_its_own_while_it_stands():
    """mobs.py SHOWN_MOTION: a monster walking in reads WL 2 and its swing A1 4, as the live client shows them (a
    take's NU 1 kept on a walker read as idle: the pursuit-mode Fane deaths, fane-death-sim-findings.md §11)."""
    mobs = Mobs(
        scene([mob(1, HELL_BOVINE, 10.0, 0.0, mode=1), mob(2, HELL_BOVINE, 90.0, 0.0, mode=1)]), random.Random(1)
    )
    seen: dict[int, set[int]] = {1: set(), 2: set()}
    for _ in range(300):
        mobs.tick(HERE, (), OPEN)
        for found in mobs.monsters():
            seen[found.unit_id].add(found.mode)
    assert {2, 4} <= seen[1]
    assert seen[2] == {1}  # far beyond its notice: it stands in the take's mode
