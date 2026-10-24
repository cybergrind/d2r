"""The arena's rules for a tier 4-5 Herald pack fight (game.py `Arena.rules`, mobs.py `Horde`; 2026-10-21,
rca/2026-10-21/herald-fight-findings.md §3.4 "what the arena lacks"): the sigil slows, pets strike and can die,
bodies block; Bind Demon makes a demon the character's. No macro runs here: the inputs are made as the actuator makes
them, and the game is played a tick at a time."""

import math
import random
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.bind import bound
from inventory_tracking.combat import revivers
from inventory_tracking.combat.sim.monsters import STRIKE
from inventory_tracking.game.view import Viewport
from tests.inventory_tracking.macros.fakes import KEYS, WINDOW
from tests.inventory_tracking.scenarios.arena.game import (
    BIND_TAKES,
    BODIES_BLOCK,
    PET_POINTS,
    PETS_FIGHT,
    SIGIL_SLOWS,
    Arena,
)
from tests.inventory_tracking.scenarios.arena.mobs import SIGIL_SLOW, Mobs, body_of
from tests.inventory_tracking.scenarios.arena.scene import Scene
from tests.inventory_tracking.scenarios.arena.situations.situation import Situation, east, open_field
from tests.inventory_tracking.scenarios.revivers.table import raised, reviver


HULK, URDAR, DEFILER = 128, 189, 744
VIEW = Viewport(WINDOW[2] / WINDOW[3])
BIND_DEMON_KEY = 'b'


def field(build) -> Scene:
    situation = Situation.on(open_field(40))
    build(situation)
    return situation.scene


def point_at(arena: Arena, at: tuple[float, float]) -> None:
    across, down = VIEW.ground(arena.here, *at)
    arena.keys.at = (WINDOW[0] + round(across * WINDOW[2]), WINDOW[1] + round(down * WINDOW[3]))


def tap(arena: Arena, key: str) -> None:
    codes = arena.keys.keycodes([key.encode()])
    assert codes is not None
    arena.keys.press(codes[0])
    arena.keys.release(codes[0])


def test_the_sigil_slow_is_half_by_the_game_data():
    assert SIGIL_SLOW == 0.5  # skills.txt 393 Param7 -50 (ln78 for velocitypercent and attackrate)


def closed(rules: tuple[str, ...]) -> float:
    """How far a Bramble Hulk 18 off closes on the character in 5 s, a sigil lying under it all the way."""
    arena = Arena(field(lambda s: s.pack(HULK, 1, at=east(18.0), spread=0.0)), seed=3, rules=rules)
    unit = arena.mobs.live()[0]
    start = arena.mobs.mobs[unit].at
    arena.sigil = (start, -1.0)  # laid a second before the play, long enough for its state to show
    gaps = []
    for _ in range(125):
        arena.sigil = (arena.mobs.mobs[unit].at, -1.0)  # kept under it
        arena.time.step()
        gaps.append(math.dist(arena.here, arena.mobs.mobs[unit].at))
    return math.dist(arena.here, start) - gaps[-1]


def test_a_monster_in_the_sigil_walks_at_half_its_speed():
    free, slowed = closed(()), closed((SIGIL_SLOWS,))
    assert free > 2.0
    assert 0.3 * free < slowed < 0.65 * free


def swings(rules: tuple[str, ...]) -> int:
    """The swings a Bramble Hulk beside the character begins in 8 s, a sigil lying under it."""
    arena = Arena(field(lambda s: s.pack(HULK, 1, at=east(2.0), spread=0.0)), seed=5, rules=rules)
    arena.life = arena.max_life = 1e9
    unit = arena.mobs.live()[0]
    arena.sigil = (arena.mobs.mobs[unit].at, -1.0)
    walker = arena.mobs.pack.walkers[unit]
    begun, doing, until = 0, walker.doing, walker.until
    for _ in range(200):
        arena.sigil = (arena.mobs.mobs[unit].at, -1.0)
        arena.time.step()
        if walker.doing == STRIKE and (doing != STRIKE or walker.until != until):
            begun += 1
        doing, until = walker.doing, walker.until
    return begun


def test_a_monster_in_the_sigil_swings_at_half_its_rate():
    free, slowed = swings(()), swings((SIGIL_SLOWS,))
    assert free >= 6
    assert slowed <= 0.65 * free


def pet_fight(life: float) -> Arena:
    def build(s: Situation) -> None:  # the pet 14 off the character (within game.py JUMP), the hulks 3 past it
        s.pack(HULK, 3, at=east(17.0), spread=2.0)
        s.companions(east(14.0), txt=DEFILER, life=life)

    arena = Arena(field(build), seed=2, rules=(PETS_FIGHT,))
    arena.life = arena.max_life = 1e9
    return arena


def test_a_pet_strikes_the_hostile_beside_it_and_takes_its_blows():
    arena = pet_fight(1e5)
    unit = arena.mobs.live()[0]
    full = arena.mobs.mobs[unit].life
    arena.clock.sleep(6.0)
    assert arena.pet_dealt > 0
    assert arena.mobs.mobs[unit].life < full
    pet = next(m for m in arena.world.monsters if m.txt_id == DEFILER)
    assert pet.life < 128  # shown in 128ths, hurt
    assert pet.max_life == round(1e5)


def test_a_pet_whose_life_runs_out_is_gone():
    arena = pet_fight(300.0)
    arena.clock.sleep(10.0)
    assert [txt for _, _, txt in arena.pet_deaths] == [DEFILER]
    assert all(m.txt_id != DEFILER for m in arena.world.monsters)


def test_a_defiler_the_macro_summons_has_the_assumed_points():
    arena = pet_fight(1e7)
    summoned = replace(next(m for m in arena.world.monsters if m.txt_id == DEFILER), unit_id=999_999)
    assert arena.pet_life(summoned) == (PET_POINTS, PET_POINTS)


def test_pets_neither_strike_nor_die_without_the_rule():
    arena = Arena(pet_fight(300.0).scene, seed=2)
    arena.life = arena.max_life = 1e9
    arena.clock.sleep(10.0)
    assert arena.pet_dealt == 0
    assert arena.pet_deaths == []


def ring(rules: tuple[str, ...]) -> Arena:
    def build(s: Situation) -> None:
        for k in range(8):
            angle = k * math.tau / 8
            s.pack(HULK, 1, at=(9.0 * math.cos(angle), 9.0 * math.sin(angle)), spread=0.0)

    arena = Arena(field(build), seed=4, rules=rules)
    arena.life = arena.max_life = 1e9
    return arena


def overlaps(arena: Arena) -> int:
    places = [arena.mobs.mobs[unit].at for unit in arena.mobs.live()]
    radius = body_of(HULK)
    return sum(1 for i, a in enumerate(places) for b in places[i + 1 :] if math.dist(a, b) < 2 * radius - 0.05)


def test_with_bodies_blocking_the_pack_stands_round_the_character_not_in_one_another():
    free, blocked = ring(()), ring((BODIES_BLOCK,))
    free.clock.sleep(6.0)
    blocked.clock.sleep(6.0)
    assert overlaps(free) > 0
    assert overlaps(blocked) == 0
    here = blocked.here
    assert all(math.dist(here, blocked.mobs.mobs[u].at) >= 1.0 + body_of(HULK) - 0.05 for u in blocked.mobs.live())


def walked(rules: tuple[str, ...]) -> float:
    """How far the character walks east in 2 s out of a ring of eight Bramble Hulks pressed round it."""

    def build(s: Situation) -> None:
        for k in range(8):
            angle = k * math.tau / 8
            s.pack(HULK, 1, at=(2.6 * math.cos(angle), 2.6 * math.sin(angle)), spread=0.0)

    arena = Arena(field(build), seed=4, rules=rules)
    arena.life = arena.max_life = 1e9
    start = arena.here
    arena.bound, arena.route = ((start[0] + 12.0, start[1]), None), []
    arena.set_out()
    arena.clock.sleep(2.0)
    return math.dist(start, arena.here)


def test_surrounded_the_character_cannot_walk_out_with_bodies_blocking():
    assert walked(()) > 5.0
    assert walked((BODIES_BLOCK,)) < 0.5


def bind_scene() -> Scene:
    def build(s: Situation) -> None:
        s.pack(URDAR, 1, at=east(8.0), spread=0.0)
        s.pack(HULK, 1, at=(0.0, 8.0), spread=0.0)
        s.companions((1.0, 1.0), txt=DEFILER, life=1e6)

    return field(build)


def test_bind_demon_on_a_demon_makes_it_the_character_s():
    arena = Arena(bind_scene(), seed=1, rules=(PETS_FIGHT,))
    urdar = next(m for m in arena.world.monsters if m.txt_id == URDAR)
    assert KEYS[382] == BIND_DEMON_KEY
    point_at(arena, (urdar.x, urdar.y + 0.5))
    tap(arena, BIND_DEMON_KEY)
    arena.clock.sleep(BIND_TAKES + 0.1)
    assert [unit for _, unit in arena.binds] == [urdar.unit_id]
    assert urdar.unit_id not in arena.mobs.live()
    assert [m.unit_id for m in bound(arena.world)] == [urdar.unit_id]


def test_bind_demon_takes_no_bramble_hulk():
    arena = Arena(bind_scene(), seed=1, rules=(PETS_FIGHT,))
    hulk = next(m for m in arena.world.monsters if m.txt_id == HULK)
    point_at(arena, (hulk.x, hulk.y + 0.5))
    tap(arena, BIND_DEMON_KEY)
    arena.clock.sleep(BIND_TAKES + 0.1)
    assert arena.binds == []
    assert hulk.unit_id in arena.mobs.live()


def test_the_rules_must_be_known():
    with pytest.raises(AssertionError):
        Arena(bind_scene(), rules=('nonsense',))


def test_a_reviver_raises_the_dead_of_its_family_after_its_table_seconds():
    # The rule REVIVERS_RAISE (game.py, mobs.py `Mobs.raise_dead`, 2026-10-23): a Fallen killed beside a Fallen Shaman
    # stands up again after the shaman's table seconds (combat/revivers.py), the same unit at full life
    shaman, fallen = reviver('fallenshaman1')['txt'], raised('FallenShaman')['fallen1']
    situation = Situation.on(open_field(40), area=3).pack(shaman, 1, at=east(20.0), spread=0.0)
    situation.pack(fallen, 1, at=east(15.0), spread=0.0)
    mobs = Mobs(situation.scene, random.Random(1))
    shaman_unit, fallen_unit = (mob.unit for mob in situation.scene.mobs)
    assert mobs.hit(fallen_unit, 1e9)
    frames = round(revivers.revivers()[shaman].seconds * 25)
    raised_at = None
    for frame in range(frames + 5):
        mobs.frame = frame
        if mobs.raise_dead():
            raised_at = frame
            break
    assert raised_at == frames
    assert fallen_unit in mobs.live()
    assert mobs.hostile.count(fallen_unit) == 1
    assert mobs.mobs[fallen_unit].life == mobs.mobs[fallen_unit].full
    assert mobs.hit(shaman_unit, 1e9)
    assert mobs.hit(fallen_unit, 1e9)
    mobs.frame += frames * 2
    assert mobs.raise_dead() == []  # the shaman dead: nobody gets up
