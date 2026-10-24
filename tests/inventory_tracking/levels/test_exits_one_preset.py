"""The way back of a level that is one fixed preset (levels/exits.py TARGET_KEEPS_WARPS, 2026-10-24): its target mark
shares the preset instance with the stairs up, which never reached the card, so the zone's climb (macros/zonenav.py
`back`) had no mark: "Anya (Crystalline Passage is not marked yet)", six "TZ up" legs that ended at once and the Town
Portal (14:09:44-14:09:46 on 2026-10-24, take 20261024T110718Z-114). Each level's preset instance as its take read it:
(preset, block x, block y, block w, block h, variant, the level it leads up to)."""

import pytest

from inventory_tracking.levels import exits
from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.routes.zone_graph import way


ONE_PRESET = {
    114: (1038, 2000, 1300, 64, 64, 1, 113),  # Frozen River (Anya), 20261024T110718Z-114
    116: (1040, 2000, 1764, 32, 32, 0, 115),  # Drifter Cavern
    119: (1041, 2000, 2376, 32, 32, 2, 118),  # Icy Cellar, 14:16:50
    16: (107, 1500, 2872, 24, 24, 0, 12),  # Pit Level 2
    15: (106, 1500, 2748, 24, 24, 0, 11),  # Hole Level 2
    14: (105, 1500, 2624, 24, 24, 0, 10),  # Underground Passage Level 2
    90: (703, 2000, 2200, 40, 40, 1, 87),  # Swampy Pit Level 3
    91: (704, 2000, 2340, 40, 40, 0, 89),  # Flayer Dungeon Level 3
    93: (747, 2500, 1300, 18, 22, 0, 92),  # Sewers Level 2
    102: (796, 3500, 1600, 41, 29, 0, 101),  # Durance of Hate Level 3
}


def card_of(area: int) -> list[tuple[str, str, int | None]]:
    preset, x, y, width, height, variant, up = ONE_PRESET[area]
    block = (x, y, width, height)
    rooms = tuple(
        Room(preset, x + dx, y + dy, 8, 8, variant, block, (up,) if (dx, dy) == (0, 0) else ())
        for dx in range(0, width, 8)
        for dy in range(0, height, 8)
    )
    guidance = guide_level(handler_for(area), LevelSnapshot(Location(area, 0, 0, 0), rooms))
    return [(poi.label, poi.kind, poi.area) for poi in guidance.pois]


@pytest.mark.parametrize('area', sorted(ONE_PRESET))
def test_a_one_preset_levels_way_back_is_on_its_card_named_as_the_climb_names_it(monkeypatch, area):
    monkeypatch.setattr(exits, 'TARGET_KEEPS_WARPS', True)
    up = ONE_PRESET[area][-1]
    mark = way(area, up).mark  # the climb's stage mark (zonenav.py `back`: node.back.mark)
    assert (mark, 'previous', up) in card_of(area)


def test_frozen_rivers_card_held_anya_alone_with_the_switch_off(monkeypatch):
    monkeypatch.setattr(exits, 'TARGET_KEEPS_WARPS', False)
    assert card_of(114) == [('Anya', 'target', None)]  # 14:07:18 "Level guide: Frozen River (unconfirmed) — Anya"
    monkeypatch.setattr(exits, 'TARGET_KEEPS_WARPS', True)
    assert card_of(114) == [('Anya', 'target', None), ('Crystalline Passage', 'previous', 113)]


def test_with_the_mark_the_climbs_stage_is_a_way_out_to_go_to_not_the_targets_stand_in():
    # 14:09:45: the pursuit's goal was "Anya (Crystalline Passage is not marked yet)", no route stage; with the way
    # back on the card the climb's stage is an ENTER goal at its stairs (pursuit.py `to_the_door`: gone to, the run
    # ends at it, the TZ up leg presses through)
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros.goals import ENTER, route_goal
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import back

    stage = back(way(114, 113).mark, 113)
    here = (10243.5, 6792.5)  # where the character stood, 14:09:44-46
    anya = Target(114, (), (2036.2, 1311.2), 'Anya', 'target')
    old = route_goal(here, spend=PRESSED, reach=20.0, stage=stage, card=anya)
    assert old is not None
    assert old.stage is None
    assert 'is not marked yet' in old.label
    stairs = Target(114, (), (2002.5, 1330.0), 'Crystalline Passage', 'previous', warp=True)
    found = route_goal(here, spend=PRESSED, reach=20.0, stage=stage, card=stairs)
    assert found is not None
    assert found.do == ENTER
    assert found.stage == stage
    assert found.place == (2002.5 * 5, 1330.0 * 5)
