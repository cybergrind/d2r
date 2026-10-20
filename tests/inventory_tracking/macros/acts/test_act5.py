"""Act 5 by its script (macros/acts/act5.py; the player, 2026-10-20 ~22:50: "act5: act5 shard -> throne -> baal ->
halls -> nihiltak -> rest of zones"): the plan pinned, the game walked, and the marks the walks up from the waypoints
take (Halls of Pain -> Halls of Anguish -> Nihlathak's Temple, Worldstone Keep 2 -> 1) on the real dumps."""

import math

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import PRESET_NAMES, preset_name
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.macros.loop import LEAVE, TZ_SHARD
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import replay
from tests.inventory_tracking.macros.acts.harness import ActGame, line_of, plan_of, trips_of
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS


HARROGATH = 109
PLAN = (
    'Macro: tz: zone Act5-Manual + Act1-Catacombs: Baal from 129: [129, 130, 131, 132], [129, 130] crossed to the '
    'boss, worked after it; Nihlathak from 123: [123, 124]; Halls of Anguish from 123: [123, 122, 121]; Worldstone '
    'Keep 1 from 129: [129, 128]; Baal from 129: [129, 130]; Bloody Foothills from 111: [111, 110]; Frozen River '
    'from 113: [113, 114]; Drifter Cavern from 115: [115, 116]; Icy Cellar from 118: [118, 119]; Pit of Acheron from '
    '112: [112]; Infernal Pit from 117: [117]; Andariel from 35: [35, 36, 37]; skipped '
)
UNREAD = 'the red portal is not in the map files: its object is not read yet'


def test_the_act_5_plan_is_baal_first_then_the_halls_then_the_rest(monkeypatch, caplog):
    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 5, rotation=CATACOMBS)
    assert any(record.getMessage().startswith(PLAN) for record in caplog.records)
    assert trips_of(plan) == [
        ('Baal', 129, (129, 130, 131, 132)),  # the Keeps crossed, the Throne's waves, the portal, Baal
        ('Nihlathak', 123, (123, 124)),  # the Halls of Pain, then Nihlathak
        ('Halls of Anguish', 123, (123, 122, 121)),  # up: the Halls of Anguish, then Pindleskin
        ('Worldstone Keep 1', 129, (129, 128)),  # the Keep 2 crossed to Baal, then up to the Keep 1
        ('Baal', 129, (129, 130)),  # the Keep 3 crossed to Baal
        ('Bloody Foothills', 111, (111, 110)),  # the Frigid Highlands, then back to the Foothills
        ('Frozen River', 113, (113, 114)),
        ('Drifter Cavern', 115, (115, 116)),
        ('Icy Cellar', 118, (118, 119)),
        ('Pit of Acheron', 112, (112,)),
        ('Infernal Pit', 117, (117,)),
        ('Andariel', 35, (35, 36, 37)),  # the rotation
    ]
    assert plan.excursions[0].passes == frozenset((129, 130))
    assert line_of(plan) in PLAN
    pits = [(125, 111), (126, 112), (127, 117)]  # the red portals' pits
    assert [(area, why) for area, why in plan.skipped if area > 100] == [
        (pit, f'pending stage {outside}→{pit}: {UNREAD}') for pit, outside in pits
    ]
    assert 'Macro: act: act 5 step' not in caplog.text  # every step played


def test_an_act_5_game_is_the_shard_baal_nihlathak_the_halls_then_the_act_then_the_rotation(monkeypatch):
    walk = ActGame(5, monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [5]
    assert walk.moves[:20] == [
        ('waypoint', 129),
        ('door', 130),
        ('door', 131),  # the Throne: stand, the waves (Lister), the portal
        ('door', 132),  # Baal
        ('portal', HARROGATH),
        ('waypoint', 123),  # the Halls of Pain
        ('door', 124),  # Nihlathak
        ('portal', HARROGATH),
        ('waypoint', 123),
        ('door', 122),  # up the Halls of Anguish
        ('door', 121),  # Nihlathak's Temple: Pindleskin
        ('portal', HARROGATH),
        ('waypoint', 129),
        ('door', 128),  # up to the Keep 1
        ('portal', HARROGATH),
        ('waypoint', 129),
        ('door', 130),  # down again: the Keep 3's own run (tzloop.py `reenter`)
        ('portal', HARROGATH),
        ('waypoint', 111),
        ('door', 110),  # the Highlands, back to the Foothills
    ]
    assert walk.waypoints[-6:] == [113, 115, 118, 112, 117, 35]
    act = [129, 130, 131, 132, 123, 124, 122, 121, 128, 111, 110, *range(113, 117), 118, 119, 112, 117]
    assert walk.levels == [*act, 35, 36, 37]
    assert walk.runs.index(129, 1) > walk.runs.index(132)  # the Keeps' own runs after Baal's
    assert walk.runs.index(130, 2) > walk.runs.index(128)
    assert walk.kills == [
        'Lister the Tormentor', 'Baal', 'Nihlathak Boss', 'Pindleskin', 'Frozenstein', 'Snapchip Shatter', 'Andariel'
    ]  # fmt: skip
    assert walk.legs[-1] == LEAVE


def named(name: str) -> int:
    [found] = [preset for preset, known in PRESET_NAMES.items() if known == name]
    return found


def test_the_halls_of_pain_dumps_mark_the_way_up_on_the_se_quadrants_stairs():
    for fixture in ('halls_of_pain_nw_down', 'halls_of_pain_live'):
        guidance = guide_level(handler_for(123), replay(fixture))
        up = next(poi for poi in guidance.pois if poi.label == 'Halls of Anguish')
        assert (up.kind, preset_name(up.room.preset), up.area) == ('previous', 'Act 5 - Temple SE up', 122)
        assert up.room.block is not None
        assert up.spot == (up.room.block[0] + 39.0, up.room.block[1] + 36.5)  # warp slot 0 of tempSE02.ds1
        assert guidance.problems == ()


def test_the_worldstone_keep_2_dump_marks_the_way_up_to_the_keep_1():
    guidance = guide_level(handler_for(129), replay('worldstone_keep_2'))
    up = next(poi for poi in guidance.pois if poi.label == 'Worldstone Keep 1')
    assert (up.kind, preset_name(up.room.preset)) == ('previous', 'Act 5 - Baal Prev NSW')


def test_nihlathaks_temple_marks_pindleskin_by_the_stairs_down():
    origin, size = (1000, 2000), 104
    block = (*origin, size, size)
    rooms = tuple(
        Room(named('Act 5 - Temple Entrance'), origin[0] + 8 * i, origin[1] + 8 * j, 8, 8, 0, block)
        for i in range(size // 8)
        for j in range(size // 8)
    )
    guidance = guide_level(handler_for(121), LevelSnapshot(Location(121, 0, 5010, 10010), rooms))

    pindleskin, stairs = guidance.pois[0], next(poi for poi in guidance.pois if poi.label == 'Halls of Anguish')
    assert (pindleskin.label, pindleskin.kind) == ('Pindleskin', 'target')
    assert math.dist(pindleskin.point, (origin[0] * TILE_UNITS + 58, origin[1] * TILE_UNITS + 35)) <= 3
    assert (stairs.kind, stairs.area, stairs.spot) == ('stairs', 122, (origin[0] + 12.0, origin[1] + 6.5))
    assert guidance.problems == ()
