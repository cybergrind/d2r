"""Clicks at doors, at townspeople and the hover record (macros/targeting.py; rca/2026-10-21/targeting-findings.md)."""

import math
import struct
from dataclasses import replace

from inventory_tracking.game.layout import HOVER_RVA
from inventory_tracking.game.records import Carried, Monster, Pack, Stocked, Thing, Warp, World
from inventory_tracking.levels.model import Room, Target
from inventory_tracking.macros import shop, targeting, teleport
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.shop import JAMELLA, KEY, SCROLL, restock
from inventory_tracking.macros.targeting import CLICK, EMPTY, LATER, WAIT, door_hover, entry_learnable, keep_mid_walk
from inventory_tracking.macros.teleport import ENTRY_MAX, WARP_NEAR, step_toward, walk_into
from tests.inventory_tracking.macros.fakes import KEYS, WINDOW, Game, player, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
ASPECT = WINDOW[2] / WINDOW[3]


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def door(point, label='Next level') -> Target:
    return Target(109, (HERE, *EAST), point, label, 'stairs', True)


# --- the rules ---


def test_what_an_aim_at_a_door_does_with_what_is_under_it():
    assert door_hover((5, 1), nothing=False, objects=False) == CLICK
    assert door_hover((2, 9), nothing=False, objects=False) == LATER  # an object beside a stairs: not the door
    assert door_hover((2, 9), nothing=False, objects=True) == CLICK  # the door's entrance is the object
    assert door_hover((1, 77), nothing=False, objects=True) == WAIT  # the mercenary: the click would go to it
    assert door_hover((4, 50), nothing=False, objects=True) == WAIT
    assert door_hover(None, nothing=True, objects=False) == EMPTY  # nothing there by the record
    assert door_hover(None, nothing=False, objects=False) == CLICK  # unread: as before


def test_the_switches_off_give_the_old_answers(monkeypatch):
    monkeypatch.setattr(targeting, 'HOVER_NOTHING', False)
    monkeypatch.setattr(targeting, 'OBJECT_DOORS', False)
    monkeypatch.setattr(targeting, 'ENTRY_FROM_WARP', False)
    assert door_hover(None, nothing=True, objects=False) == CLICK
    assert not targeting.object_door((), (0.0, 0.0), WARP_NEAR)
    assert not entry_learnable((-9.0, -7.0), (-6.0, -5.0), ENTRY_MAX)


def test_a_door_with_no_warp_tile_near_its_mark_has_an_object_for_its_entrance():
    mark = (5007.5, 5002.5)
    assert targeting.object_door((), mark, WARP_NEAR)
    assert not targeting.object_door((Warp(3, 10, 5011.0, 5000.0),), mark, WARP_NEAR)
    assert targeting.object_door((Warp(3, 10, 5040.0, 5000.0),), mark, WARP_NEAR)  # another door's, far off
    assert not targeting.object_door(None, mark, WARP_NEAR)  # unread: nothing said


def test_an_entry_far_from_the_mark_is_the_doors_own_when_near_its_warp_unit():
    # Flayer Dungeon 1, 7 entries of 2026-10-19/20: the level changed at (-9, -7) from the mark, 11.4 away
    assert entry_learnable((-3.0, 2.0), None, ENTRY_MAX)
    assert not entry_learnable((-9.0, -7.0), None, ENTRY_MAX)  # no warp unit known
    assert entry_learnable((-9.0, -7.0), (-6.0, -5.0), ENTRY_MAX)
    assert not entry_learnable((-9.0, -7.0), (4.0, 3.0), ENTRY_MAX)  # the warp unit on the other side
    assert not entry_learnable((-15.0, -2.0), (-12.0, -1.0), ENTRY_MAX)  # past ENTRY_FAR


def test_a_menu_is_kept_when_the_view_moved_under_half_a_line():
    assert keep_mid_walk(0.005, shop.LINE)
    assert not keep_mid_walk(0.012, shop.LINE)
    assert not keep_mid_walk(None, shop.LINE)


def hover_memory(records):
    from inventory_tracking.game.memory import GameMemory

    memory = object.__new__(GameMemory)
    memory.base, memory.hover_raw = 0x1000, None
    reads = iter(records)

    def read(address, size):
        assert (address, size) == (0x1000 + HOVER_RVA - 4, 16)
        found = next(reads)
        if found is None:
            raise OSError('unreadable')
        return struct.pack('<IIII', *found)

    memory.read = read
    return memory


def test_the_hover_record_tells_nothing_under_the_pointer_from_unreadable():
    memory = hover_memory([(0x101, 5, 9, 0), (0, 5, 9, 0), None])
    assert memory.hovered() == (5, 9)
    assert not memory.nothing_hovered()
    assert memory.hovered() is None
    assert memory.nothing_hovered()  # read, and it names nothing
    assert memory.hovered() is None
    assert not memory.nothing_hovered()  # unreadable: nothing is known


# --- doors ---


def object_door_game() -> tuple[Game, Run]:
    """The Durance of Hate's stairs: the entrance an object (2, 9) drawn 60 pixels above its mark, no warp tile."""
    play = Game(world())
    play.door, play.door_above = (1001.5, 1000.5), 60
    run = play.run()
    run.warps = lambda: ()

    def hovered():
        found = play.unit_under_pointer()
        return (2, 9) if found == (5, 1) else None if found == (0, 0) else found

    run.hovered = hovered
    run.hover_nothing = lambda: play.unit_under_pointer() == (0, 0)
    return play, run


def test_a_door_whose_entrance_is_an_object_is_clicked_on_it_and_never_on_the_bare_ground():
    # 2026-10-19/21: Durance of Hate and the Kurast temples, 2.0-3.8 s an entry, the (0, 0) aim with nothing under it
    # clicked first and walking the character to the mark's ground
    play, run = object_door_game()
    step_toward(run, door(play.door), keys)
    assert play.character.area == 110
    assert play.walks == []  # no click on the ground
    assert [event[0] for event in play.keys.events].count('click') == 1


def test_with_the_switches_off_the_bare_ground_is_clicked_first(monkeypatch):
    monkeypatch.setattr(targeting, 'HOVER_NOTHING', False)
    monkeypatch.setattr(targeting, 'OBJECT_DOORS', False)
    play, run = object_door_game()
    step_toward(run, door(play.door), keys)
    assert play.character.area == 110
    assert play.walks  # the old way: a walk to the mark's ground first


def test_an_entry_11_units_from_the_mark_beside_its_warp_unit_is_remembered():
    mark = door((1001.5, 1000.5), 'Flayer Dungeon 1')
    at = (5007.5, 5002.5)
    play = Game(world(player=player(x=at[0] - 9.0, y=at[1] - 7.0)))
    play.door = (1001.5, 1000.5)
    run = play.run()
    run.warps = lambda: (Warp(3, 999, at[0] - 6.0, at[1] - 5.0),)  # no click box known for it
    walk_into(run, mark, play.character, ASPECT)
    assert play.character.area == 110
    found = teleport.ENTRIES.offset(mark)
    assert found is not None
    assert math.dist(found, (-9.0, -7.0)) < 0.1


def test_flayer_dungeon_1_has_its_entry_seeded():
    assert teleport.KNOWN_ENTRIES['preset 602:stairs:Flayer Dungeon 1'] == (-9.0, -7.0)


# --- townspeople ---

FORTRESS = 103
START = (5048.0, 5044.0)
JAMELLA_AT = (5083.5, 5058.5)
WAYPOINT = Thing(6, 398, 2, 5044.0, 5019.0)
STOCK = (Stocked(KEY, 3, 9, 5), Stocked(SCROLL, 3, 9, 4), Stocked(SCROLL, 3, 9, 3))


class Vendor(Game):
    """Jamella as the 08:10:04 Cain: the first `walks_off` clicks on her walk the character up while she walks on, and
    no menu opens; `mid_walk`: her menu opens as the character still walks, `drift` units short of where it stands."""

    def __init__(self, start: World) -> None:
        super().__init__(start)
        self.walks_off = 0
        self.mid_walk = False
        self.drift = 0.0
        self.clicked_at: list[float] = []
        self.escapes_before_trade = 0

    def act(self, event) -> None:
        w = self.world
        if event[0] == 'key' and event[1] == 'Escape' and 'npc_shop' not in w.open_panels and w.open_panels:
            self.escapes_before_trade += 1
        if event[0] == 'click' and w.in_game and self.vendor is not None and not w.open_panels:
            x, y = event[1]
            if self.vendor_under(x, y):
                self.clicked_at.append(self.clock.now)
                her = self.vendor
                if self.walks_off:
                    self.walks_off -= 1
                    me = replace(self.character, x=her.x - 3.0, y=her.y)
                    self.vendor = replace(her, x=her.x + 6.0)
                    monsters = tuple(self.vendor if m.unit_id == her.unit_id else m for m in w.monsters)
                    self.world = replace(w, player=me, monsters=monsters)
                    return
                if self.mid_walk:
                    self.mid_walk = False
                    walking = replace(self.character, x=her.x - 3.0 - self.drift, y=her.y, mode=3)
                    self.world = replace(w, player=walking, open_panels=('npc_interact',))
                    stand = replace(walking, x=her.x - 3.0, mode=1)
                    self.later(0.15, lambda: setattr(self, 'world', replace(self.world, player=stand)))
                    return
        super().act(event)


def fortress() -> Vendor:
    jamella = Monster(77, JAMELLA, 1, *JAMELLA_AT, 0xFFFFFFFF)
    play = Vendor(world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]), monsters=(jamella,)))
    play.vendor, play.stock, play.thing = jamella, STOCK, WAYPOINT
    play.pack = Pack((Carried(1, CUBE_CLASS, 0, 0, (2, 2)),), ('...',) * 4, keys=1, portals=2)
    return play


def test_a_click_on_her_that_brings_no_menu_is_made_again_once_the_character_stands():
    play = fortress()
    play.walks_off = 1
    restock(play.run())
    assert play.pack is not None
    assert play.pack.keys == 24
    assert len(play.clicked_at) >= 2
    assert play.clicked_at[1] - play.clicked_at[0] < 2.0  # not MENU_SECONDS (5 s) of waiting


def test_a_menu_open_before_the_stand_is_kept_when_the_view_hardly_moved():
    play = fortress()
    play.mid_walk, play.drift = True, 0.2
    restock(play.run())
    assert play.pack is not None
    assert play.pack.keys == 24
    assert play.escapes_before_trade == 0  # not closed and opened again
    assert len(play.clicked_at) == 1


def test_a_menu_open_far_short_of_the_stand_is_opened_again_standing():
    play = fortress()
    play.mid_walk, play.drift = True, 3.0
    restock(play.run())
    assert play.pack is not None
    assert play.pack.keys == 24
    assert play.escapes_before_trade == 1
    assert len(play.clicked_at) == 2
