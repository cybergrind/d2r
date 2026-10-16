"""A scripted game for macro tests: a fake X connection and a world that reacts to its events."""

import math
import random
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from typing import Any

from inventory_tracking.builds.characters import LAYERS
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import (
    BLADE_WARP,
    CONSUME,
    DEATH_MARK,
    ECHOING_STRIKE,
    ENGORGE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SIGIL_LETHARGY,
    SUMMON_DEFILER,
)
from inventory_tracking.input.keyboard import MODIFIER_NAMES
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import HELL_GATE, PORTAL, TOWN_PORTAL
from inventory_tracking.macros.actuator import Actuator
from inventory_tracking.macros.build import Build, choose
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import Drop, Loot, Monster, Player, Teleport, Thing, World


KEYS = {SUMMON_DEFILER: 'q', CONSUME: '6', HEX_PURGE: 'g', PSYCHIC_WARD: 'r', SWAP_WEAPONS: 'c', TELEPORT: 't'}
KEYS[SIGIL_LETHARGY] = 'Button9'  # mouse 5, as CybergrindAA's key file
KEYS[ECHOING_STRIKE] = '7'  # bound by the user on 2026-10-09 so Quick Cast aims it with the pointer
KEYS[DEATH_MARK] = 'd'
KEYS[ENGORGE] = 'e'
KEYS[BLADE_WARP] = 'w'
[BUILD] = LAYERS  # the build of the fakes' character: the Echoing Strike Warlock as CybergrindAA plays it


def warlock(world: World | None) -> Build:
    """The Echoing Strike Warlock as the character in `world` plays it: with its weapon sets for a
    character the macros know, without any for another (and with no character). What every hunt and
    run played before the runner chose the build, whatever was on the keys."""
    return ECHOING_STRIKE_BUILD if world is None else choose(LAYERS, world, ECHOING_STRIKE_BUILD)


STRIKE_RANGE = 4.0  # world units: a monster this near the blades' line to the pointer is struck
ACTING_SECONDS = 0.3  # the cast animation
KEPT_KEYS = frozenset('dq6gew')  # the Quick Cast skill keys of the fakes' character but Teleport (`keeps_keys`)
PREBUFF_SET, OTHER_SET = ('fla', 'uit'), ('6cs', 'wa3')  # Heart of the Oak + Spirit; Naj's Puzzler + Codex
SLOTS = (379, 390, 375, 384, 389, 220, 393, 377, None, 382, 387, 54, 381, None, None, None)
HUNT_SLOTS = (*SLOTS[:13], ECHOING_STRIKE, *SLOTS[14:])  # with Echoing Strike on a key, as since 2026-10-09
WINDOW = (1920, 0, 2560, 1418)

# What the fake connection sends the game: ('key', name), ('click', fraction), ('button', n, fraction, held
# key names), and ('held', input) for a skill input the game sees down (`Game.read`).
Event = tuple[Any, ...]


class FakeConnection:
    """Records events as ('key', name), ('move', x, y) and ('click',); `on_event` may react."""

    def __init__(self) -> None:
        self.open_ms = 0.0
        self.events: list[Event] = []
        self.down: list[int] = []
        self.buttons_down: set[int] = set()
        self.hold_serial = 0  # counts presses of keys and buttons: a game casting once per press looks at it
        self.held: bool | Iterable[str] = False
        self.at = (2500, 900)
        self.names: dict[str, int] = {}
        self.shift = False  # Shift was down at the last left click
        self.on_event: Callable[[Event], object] = lambda event: None

    def code(self, name: str) -> int:
        """The keycode of a key name, given the first time it is asked for."""
        self.names.setdefault(name, len(self.names) + 10)
        return self.names[name]

    def keycodes(self, names: Sequence[bytes]) -> list[int] | None:
        codes = []
        for name in names:
            text = name.decode()
            if text == 'unknown':
                return None
            codes.append(self.code(text))
        return codes

    def any_key_held(self) -> bool:
        return bool(self.held_keys())

    def held_keys(self) -> frozenset[int]:
        """`held`: True for some key of the player's, or the names of the keys that are down."""
        other = {1} if self.held is True else {self.code(name) for name in self.held or ()}
        return frozenset(self.down) | other

    def modifier_keys(self) -> frozenset[int]:
        """The modifier keys (`MODIFIER_NAMES`) that are down."""
        known = {self.names.get(name.decode()) for name in MODIFIER_NAMES}
        return frozenset(code for code in self.down if code in known)

    def focused_window_pid(self) -> int | None:
        return 1

    def focused_window_rect(self) -> tuple[int, int, int, int]:
        return WINDOW

    def pointer(self) -> tuple[int, int]:
        return self.at

    def pointer_state(self) -> tuple[int, int, int]:
        return (*self.at, 0)

    def move_pointer(self, x: int, y: int) -> bool:
        self.at = (x, y)
        return True

    def _emit(self, event: Event) -> None:
        self.events.append(event)
        self.on_event(event)

    def press(self, key: int) -> bool:
        self.down.append(key)
        self.hold_serial += 1
        return True

    def down_names(self) -> set[str]:
        return {name for name, value in self.names.items() if value in self.down}

    def release(self, key: int) -> bool:
        if key in self.down:
            self.down.remove(key)
            self._emit(('key', next(name for name, value in self.names.items() if value == key)))
        return True

    def button(self, button: int, down: bool) -> bool:
        """A release is ('click', window fraction) for the left button, ('button', n, fraction, held
        key names) for any other; `shift` says whether Shift was down for the left click."""
        if down:
            self.buttons_down.add(button)
            self.hold_serial += 1
            return True
        self.buttons_down.discard(button)
        names = tuple(name for name, value in self.names.items() if value in self.down)
        self.shift = 'Shift_L' in names
        self._emit(('click', self.fraction()) if button == 1 else ('button', button, self.fraction(), names))
        return True

    def sync(self) -> None:
        pass

    def fraction(self) -> tuple[float, float]:
        return (self.at[0] - WINDOW[0]) / WINDOW[2], (self.at[1] - WINDOW[1]) / WINDOW[3]


NPC = Monster(7, 513, 1, 5010.0, 5010.0, 0xFFFFFFFF)  # a town resident


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def player(area: int = 109, **changes: Any) -> Player:
    return replace(Player(1, 'CybergrindAA', 5, area, 5000.0, 5000.0, False), **changes)


def world(area: int = 109, **changes: Any) -> World:
    return replace(World(True, (), 'cyber32', SLOTS, player=player(area)), **changes)


def character_of(world: World) -> Player:
    """The character of a world in a game: what a test reads of it there has to show."""
    assert world.player is not None
    return world.player


class Game:
    """A world that changes the way the game does when the macro's events arrive."""

    def __init__(self, start: World):
        self.world = start
        self.keys = FakeConnection()
        self.keys.on_event = self.react
        self.clock = Clock()
        self.focused = True
        self.said: list[str] = []
        self.next_unit = 100
        self.consume_takes: int | None = None  # unit id Consume removes instead of the Defiler aimed at
        self.field_focused = False
        self.sets: list[tuple[str, ...]] = [PREBUFF_SET, OTHER_SET]  # the first is in hand
        # The build a run of this game plays (`run`), as the runner would have chosen it. None: the
        # Echoing Strike Warlock as the character in the game plays it (`warlock`).
        self.build: Build | None = None
        self.loading_seconds = 6.0
        self.gold_radius = 3.0  # world units from a gold pile at which standing takes it; 0: only a click does
        self.view_marks = True  # the view byte goes to 0 while the game loads
        self.ignored: list[Event] = []
        self.deaf = False  # the loading screen: the game exists and takes no input
        self.loaded_at: float | None = None
        self.loaded = 0.0  # when the game came up
        self.blocked: Callable[[float, float], bool] = lambda x, y: (
            False
        )  # window fractions where a summon cannot stand
        self.deaf_clicks = 0  # clicks the lobby ignores while it is still coming up
        self.staff: Teleport | None = None  # the worn Teleport staff; None: Teleport as a skill, if in a slot
        self.door: tuple[float, float] | None = None  # a warp, in tiles: a click near it walks the character in
        self.swallowed_clicks = 0  # clicks in a game the game takes no notice of (a cast ends)
        self.door_above = 0.0  # classic pixels (600 high) the door is clicked above its tile; 0: on the ground
        # an object a mark names: a click on its picture sends the character through (a portal) or opens it
        self.thing: Thing | None = None
        self.thing_above = 45.0  # classic pixels its picture is clicked above its ground
        self.next_area = 110
        # Town Portal (`x`, as CybergrindAA's tome): seconds from the cast to the portal open beside the character
        # (mode 1 while it opens, 2 open: objects.txt Selectable2); None: the tome casts nothing (empty).
        self.portal_opens: float | None = 0.5
        # The waypoint panel: (tab, row) -> the level it takes the character to, the rows greyed (not got), the
        # act of each level the panel opens on, and the tab shown.
        self.waypoint_rows = {(2, 0): 75, (2, 4): 79, (3, 0): 103}
        self.greyed: set[tuple[int, int]] = set()
        self.acts = {75: 2, 79: 2, 103: 3}
        self.panel_act: int | None = None
        # Seconds a level change by a waypoint row or a portal loads, its view byte 0 meanwhile; None: no load
        # shown (the byte stays as it was). `arrived_at`: the clock of the last such change.
        self.arrival_load: float | None = None
        self.arrived_at: float | None = None
        self.sigils: list[tuple[float, float]] = []  # ground points Sigil: Lethargy was cast at
        self.engorges: list[tuple[float, float]] = []  # ground points Engorge was cast at
        self.purges: list[float] = []  # clock times Hex: Purge was cast
        self.wards: list[float] = []  # and Psychic Ward
        self.unhurt: set[int] = set()  # unit ids a hit takes no life from (a bird in the air, an immune)
        self.warps: list[tuple[float, float]] = []  # ground points Blade Warp took the character to
        self.warp_lands = True  # a Blade Warp moves the character
        self.purge_shows = True  # the character's state shows the buff after a cast
        self.strikes: list[
            tuple[int | None, tuple[float, float]]
        ] = []  # (unit id or None, ground point) per Shift+click
        self.strike_skill: int = (
            ECHOING_STRIKE  # the skill whose held input is a strike: the attack's of the build played
        )
        self.toughness: dict[int, int] = {}  # unit id -> strikes it survives (default: dies to the first)
        self.acting_until: float | None = None  # the cast animation: the player's mode is 7 until then
        self.arrivals: list[
            tuple[float, Callable[[], object]]
        ] = []  # (clock time, callable): what happens in the game on its own, in time order
        self.marks: list[int | None] = []  # unit ids Death Mark was cast on (the monster nearest the pointer), or None
        self.walks: list[tuple[float, float]] = []  # ground points clicked in a game: the character walks there at once
        self.repeats = True  # a held skill input casts again and again (the game); False: once per press
        self.struck_hold: int | None = None  # the press the last cast came from (hold_serial)
        self.reading = False
        self.loot = Loot()  # the drops, the belt and the life (the pickup step); a click on a drop's ground picks it up
        self.picked: list[str] = []  # labels of the drops picked up
        self.hover_known = True  # the game's record of the unit under the pointer can be read
        self.deaf_picks = 0  # clicks on a drop the game takes nothing from (a cast was ending)
        # None: Teleport is cast the moment its key comes, as most tests want it. True/False: a key during
        # a cast is kept and cast when that cast is over (with the pointer where it is then), or dropped.
        self.keeps_keys: bool | None = None
        self.kept_hop = False
        self.kept: list[Event] = []  # inputs that came during a cast: each is cast when the one before is over
        self.home_skill: tuple[int | None] | None = (
            None  # (the right button's skill before a kept key's cast,), while that cast runs
        )
        self.hops_cast_at: list[float] = []  # clock times the game cast a kept Teleport key
        self.slipped_picks = 0  # clicks on a drop's label that walk the character to the ground behind it
        self.pick_above = 14.0  # classic pixels a drop is clicked above its ground (host, 2026-10-10)
        self.label_above: dict[
            int, float
        ] = {}  # unit id -> the same for one drop: a pile shifts its labels (host, 21:10)
        self.belt_after: dict[
            int, tuple[int | None, ...]
        ] = {}  # drops picked up so far -> the belt from then on (a potion lands in it)

    @property
    def character(self) -> Player:
        """The character in the game (`character_of`)."""
        return character_of(self.world)

    def hop(self) -> None:
        """Teleport: the character is where the pointer's ground is, if the skill can be cast."""
        w = self.world
        charged = self.staff is not None and self.staff.in_hand and self.staff.charges > 0
        if charged or (self.staff is None and 54 in w.slots):
            x, y = self.ground_under_pointer()
            self.world = replace(w, player=replace(character_of(w), x=x, y=y))
            if self.staff is not None:
                self.staff = replace(self.staff, charges=self.staff.charges - 1)

    def react(self, event: Event) -> None:
        self.read()
        if self.acting_until is not None and self.kept_by_the_game(event):
            self.kept.append(event)  # cast when the cast under way is over (`read`)
            return
        self.act(event)

    def kept_by_the_game(self, event: Event) -> bool:
        """Whether the game keeps this input for the end of the cast under way: a Quick Cast skill key
        or the sigil's mouse button (the client's two-entry queue, macros/plan.md 2026-10-12)."""
        if not self.world.in_game or self.deaf or len(self.kept) >= 2:
            return False
        return (event[0] == 'key' and event[1] in KEPT_KEYS) or (event[0] == 'button' and event[1] == 9)

    def act(self, event: Event) -> None:
        w = self.world
        if self.deaf:
            self.ignored.append(event)
            return
        if event[0] == 'key':
            key = event[1]
            if not w.in_game:  # the lobby's game name field; its text is the name in memory
                if self.field_focused:
                    name = w.game_name
                    if key == 'BackSpace':
                        self.world = replace(w, game_name=name[:-1])
                    elif key == 'Return':  # the loading screen: in the game, not playable yet
                        self.world = world(game_name=name, monsters=(NPC,), view=0 if self.view_marks else 255)
                        self.deaf = True
                        self.loaded_at = self.clock.now + self.loading_seconds
                    elif len(key) == 1:
                        self.world = replace(w, game_name=name + key)
            elif key == 'c':
                self.sets.reverse()
                if self.staff is not None:
                    self.staff = replace(self.staff, in_hand=not self.staff.in_hand)
            elif key == 't' and self.keeps_keys is not None and self.acting_until is not None:
                # During a cast: the game keeps the key and casts it when the cast is over, or drops it.
                self.kept_hop = self.keeps_keys
            elif key == 't':
                self.hop()
            elif key == 'x' and w.in_game and self.portal_opens is not None:
                self.next_unit += 1
                me = character_of(w)
                self.thing = Thing(self.next_unit, TOWN_PORTAL, 1, me.x + 3.0, me.y - 2.0)
                self.arrivals.append((self.clock.now + self.portal_opens, self.open_portal))
            elif key == 'd' and DEATH_MARK in w.slots:
                x, y = self.under_pointer()
                foes = [m for m in w.monsters if m.txt_id not in (744, 700) and math.hypot(m.x - x, m.y - y) < 4]
                self.marks.append(min(foes, key=lambda m: math.hypot(m.x - x, m.y - y)).unit_id if foes else None)
            elif key in '1234' and w.in_game:  # a belt column: its potion is drunk, the life is full
                belt = list(self.loot.belt)
                belt[int(key) - 1] = None
                self.loot = replace(self.loot, belt=tuple(belt), life=self.loot.max_life)
            elif key == 'Escape':
                panels = () if w.open_panels else ('quit_menu',)
                self.world = replace(w, open_panels=panels)
            elif key == 'q' and self.blocked(*self.keys.fraction()):
                pass
            elif key == 'q':
                self.next_unit += 1
                x, y = self.under_pointer()
                kept = tuple(m for m in w.monsters if m.txt_id != 744)
                # A Defiler summoned over a standing one cancels Consume (user, 2026-10-06).
                buffed = bool(character_of(w).consume) and len(kept) == len(w.monsters)
                self.world = replace(
                    w,
                    monsters=(*kept, Monster(self.next_unit, 744, 1, x, y, 0xFFFFFFFF, ally=True)),
                    player=replace(character_of(w), consume=buffed),
                )
            elif key == 'e':
                self.engorges.append(self.ground_under_pointer())
            elif key == 'w' and BLADE_WARP in w.slots and self.warp_lands:
                # Blade Warp: the character is where the pointer's ground is (what a run in the game has to show)
                x, y = self.ground_under_pointer()
                self.warps.append((x, y))
                self.world = replace(w, player=replace(character_of(w), x=x, y=y))
            elif key == 'g' and w.in_game:  # Hex: Purge: the buff is on (where the test reads its state at all)
                self.purges.append(self.clock.now)
                if character_of(w).hex_purge is not None and self.purge_shows:
                    self.world = replace(w, player=replace(character_of(w), hex_purge=True))
            elif key == 'r' and w.in_game:  # Psychic Ward, as Hex: Purge above
                self.wards.append(self.clock.now)
                if character_of(w).ward is not None and self.purge_shows:
                    self.world = replace(w, player=replace(character_of(w), ward=True))
            elif key == '6':
                hit = self.consume_takes or self.pet_under_pointer()
                if hit is not None:
                    left = tuple(m for m in w.monsters if m.unit_id != hit)
                    self.world = replace(w, monsters=left, player=replace(character_of(w), consume=True))
        elif event[0] == 'button' and event[1] == 9 and w.in_game:
            self.sigils.append(self.ground_under_pointer())
        elif event[0] == 'held':  # a skill input down while the character is free: the game casts it
            if event[1] in (KEYS.get(self.strike_skill), 'Button3') or character_of(w).left_skill == self.strike_skill:
                self.strike()
            else:  # the plain attack, in place: an animation and nothing hit (host, 20:07 on 2026-10-09)
                self.world = replace(w, player=replace(character_of(w), mode=7))
                self.acting_until = self.clock.now + ACTING_SECONDS
        elif event[0] == 'click' and w.in_game and self.keys.shift:
            pass
        elif event[0] == 'click':
            x, y = event[1]
            if w.quit_menu and abs(x - 0.5) < 0.08 and abs(y - 0.438) < 0.02:
                self.world = World(False, (), w.game_name, w.slots)
            elif not w.in_game and 0.67 < x < 0.85 and abs(y - 0.158) < 0.011:
                if self.deaf_clicks:
                    self.deaf_clicks -= 1
                else:
                    self.field_focused = True
            elif w.in_game and 'waypoint' in w.open_panels:
                self.panel_click(x, y)
            elif w.in_game and self.swallowed_clicks:
                self.swallowed_clicks -= 1  # a cast was ending: the game takes no notice
            elif w.in_game:
                gx, gy = self.ground_under_pointer()
                door = None if self.door is None else (self.door[0] * 5, self.door[1] * 5)
                if door and self.door_under_pointer():
                    self.world = replace(w, player=replace(character_of(w), area=self.next_area, x=door[0], y=door[1]))
                elif self.thing is not None and self.thing_under_pointer():
                    if self.thing.txt_id == TOWN_PORTAL and self.thing.mode != 2:
                        pass  # still opening: not selectable yet
                    elif self.thing.txt_id in WAYPOINT_CLASSES:  # the walk to it, and its panel on its act
                        me = replace(character_of(w), x=self.thing.x + 2.0, y=self.thing.y + 2.0)
                        self.world = replace(w, player=me, open_panels=('waypoint',))
                        self.panel_act = self.acts.get(me.area)
                    elif self.thing.txt_id in (PORTAL, HELL_GATE, TOWN_PORTAL):
                        self.arrive(self.next_area)
                    else:
                        self.thing = replace(self.thing, mode=2)
                elif (drop := self.drop_under_pointer()) is not None and self.deaf_picks:
                    self.deaf_picks -= 1
                elif drop is not None and self.slipped_picks:
                    self.slipped_picks -= 1  # the click landed under the label: a walk to that ground
                    self.walks.append((gx, gy))
                    self.world = replace(w, player=replace(character_of(w), x=gx, y=gy))
                elif drop is not None:
                    self.picked.append(drop.label)
                    self.loot = replace(self.loot, drops=tuple(d for d in self.loot.drops if d is not drop))
                    if len(self.picked) in self.belt_after:
                        self.loot = replace(self.loot, belt=self.belt_after[len(self.picked)])
                    self.world = replace(w, player=replace(character_of(w), x=drop.x, y=drop.y))
                elif (
                    math.dist((gx, gy), (character_of(w).x, character_of(w).y)) < 40
                ):  # a click on the ground: a walk there
                    self.walks.append((gx, gy))
                    self.world = replace(w, player=replace(character_of(w), x=gx, y=gy))

    def panel_click(self, x: float, y: float) -> None:
        """A click in the open waypoint panel, by its layout (waypointspanelexpansionhd.json, restated here): a tab
        shows its act; a row of the act shown that is not greyed takes the character to its level, the panel closed."""
        width, height = WINDOW[2], WINDOW[3]
        scale = height / 2160
        px = x * width / scale - 236  # layout units from the panel's corner
        py = (y * height - 0.397 * height) / scale + 651
        if 201 <= py <= 271 and 148 <= px < 148 + 5 * 173:
            self.panel_act = int((px - 148) // 173)
            return
        row, inside = divmod(py - 264, 123)
        if 152 <= px <= 1000 and row >= 0 and inside <= 100 and self.panel_act is not None:
            key = (self.panel_act, int(row))
            if key in self.waypoint_rows and key not in self.greyed:
                self.world = replace(self.world, open_panels=())
                self.arrive(self.waypoint_rows[key])

    def arrive(self, area: int) -> None:
        """A level change by a portal or a waypoint row: the area at once, and the load (`arrival_load`) after it."""
        self.world = replace(self.world, player=replace(character_of(self.world), area=area))
        self.arrived_at = self.clock.now
        if self.arrival_load is not None:
            self.world = replace(self.world, view=0)
            self.arrivals.append((self.clock.now + self.arrival_load, self.loaded_level))

    def loaded_level(self) -> None:
        self.world = replace(self.world, view=255)

    def open_portal(self) -> None:
        if self.thing is not None and self.thing.txt_id == TOWN_PORTAL:
            self.thing = replace(self.thing, mode=2)

    def door_under_pointer(self) -> bool:
        """Whether the pointer is on the door (`door_above` pixels above its tile), within a walk."""
        if self.door is None:
            return False
        gx, gy = self.ground_under_pointer()
        door, player = (self.door[0] * 5, self.door[1] * 5), self.character
        lift = self.door_above / 16  # a pixel down the screen is 1/16 of a unit along both axes
        return math.dist((gx + lift, gy + lift), door) < 5 and math.dist((player.x, player.y), door) < 30

    def thing_under_pointer(self) -> bool:
        """Whether the pointer is on the object's picture (`thing_above` pixels above its ground), within a walk."""
        if self.thing is None:
            return False
        gx, gy = self.ground_under_pointer()
        at, player = (self.thing.x, self.thing.y), self.character
        lift = self.thing_above / 16
        return math.dist((gx + lift, gy + lift), at) < 2 and math.dist((player.x, player.y), at) < 30

    def unit_under_pointer(self) -> tuple[int, int]:
        """(unit type, unit id) under the pointer: a door's tile, an object, a drop, else nothing."""
        if self.door_under_pointer():
            return (5, 1)
        if self.thing is not None and self.thing_under_pointer():
            return (2, self.thing.unit_id)
        drop = self.drop_under_pointer()
        return (4, drop.unit_id) if drop else (0, 0)

    def drop_under_pointer(self) -> Drop | None:
        """The drop whose ground the pointer is on (`pick_above` pixels above it), within a walk."""
        gx, gy = self.ground_under_pointer()
        player = self.character
        for drop in self.loot.drops:
            lift = self.label_above.get(drop.unit_id, self.pick_above) / 16
            near = math.dist((gx + lift, gy + lift), (drop.x, drop.y)) < 0.5
            if near and math.dist((player.x, player.y), (drop.x, drop.y)) < 40:
                return drop
        return None

    def held_input(self) -> str | None:
        """The strike's input (Echoing Strike's, unless `strike_skill` says another) held right now, as
        `react` names it, or None."""
        w, keys = self.world, self.keys
        key = KEYS.get(self.strike_skill)
        if key in keys.down_names() and self.strike_skill in w.slots:
            return key
        if 3 in keys.buttons_down and character_of(w).right_skill == self.strike_skill:
            return 'Button3'
        if 1 in keys.buttons_down and 'Shift_L' in keys.down_names():
            return 'Shift+click'
        return None

    def strike(self) -> None:
        """Echoing Strike toward the pointer: the blades fly from the character to the ground under it
        and meet there; the hostile nearest their line, within STRIKE_RANGE of it, takes a hit."""
        w = self.world
        x, y = self.ground_under_pointer()
        p = (character_of(w).x, character_of(w).y)

        def off_line(m: Monster) -> float:
            length = math.dist(p, (x, y)) or 1.0
            t = max(0.0, min(1.0, ((m.x - p[0]) * (x - p[0]) + (m.y - p[1]) * (y - p[1])) / length**2))
            return math.dist((m.x, m.y), (p[0] + (x - p[0]) * t, p[1] + (y - p[1]) * t))

        foes = [m for m in w.monsters if m.txt_id not in (744, 700) and off_line(m) < STRIKE_RANGE]
        hit = min(foes, key=off_line) if foes else None
        self.strikes.append((hit.unit_id if hit else None, (x, y)))
        monsters, dead = w.monsters, w.dead
        if hit is not None:
            left = self.toughness.get(hit.unit_id, 1) - 1
            self.toughness[hit.unit_id] = left
            if left > 0 and hit.max_life and hit.life > 1 and hit.unit_id not in self.unhurt:
                # A hit that does not kill shows in the life the client has of it.
                monsters = tuple(replace(m, life=m.life - 1) if m.unit_id == hit.unit_id else m for m in monsters)
            if left <= 0:
                monsters = tuple(m for m in monsters if m.unit_id != hit.unit_id)
                dead = dead | {hit.unit_id}  # it lies there: a kill, not a unit that only left memory
        self.world = replace(w, monsters=monsters, dead=dead, player=replace(character_of(w), mode=7))
        self.acting_until = self.clock.now + ACTING_SECONDS

    def under_pointer(self) -> tuple[float, float]:
        """World position drawn under the pointer (the inverse of routines.screen_fraction)."""
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        a = (fx - 0.5) * aspect * 600 / 16
        b = (fy - 0.494 + 0.035) * 600 / 8
        p = self.character
        return p.x + (a + b) / 2, p.y + (b - a) / 2

    def ground_under_pointer(self) -> tuple[float, float]:
        """World position of the ground under the pointer (the inverse of teleport.ground_fraction)."""
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        a = (fx - 0.5) * aspect * 600 / 16
        b = (fy - 0.494) * 600 / 8
        p = self.character
        return p.x + (a + b) / 2, p.y + (b - a) / 2

    def pet_under_pointer(self) -> int | None:
        """Consume takes the demon nearest the pointer, the bound one as readily as a Defiler."""
        x, y = self.under_pointer()
        # The bound demon is tall: drawn below the pointer, its body still covers it (host, 2026-10-07).
        for m in self.world.monsters:
            across, down = (m.x - m.y) - (x - y), (m.x + m.y) - (x + y)
            if m.txt_id == 700 and abs(across) < 6 and 0 <= down < 18:
                return m.unit_id
        near = [m for m in self.world.monsters if m.txt_id in (744, 700) and math.hypot(m.x - x, m.y - y) < 5]
        return min(near, key=lambda m: math.hypot(m.x - x, m.y - y)).unit_id if near else None

    def run(self, seed: int = 1) -> Run:
        pace = Pace(random.Random(seed), self.clock.sleep)
        run = Run(
            self.read,
            Actuator(self.keys, lambda: self.focused, pace),
            pace,
            clock=self.clock,
            say=self.said.append,
            hands=lambda: self.sets[0],
            teleport=lambda: self.staff,
            loot=lambda: self.loot,
            build=self.build if self.build is not None else warlock(self.world),
        )
        if self.build is None and self.world.player is None:
            # From the lobby the character shows only in the game: the build is the one of the first look
            # that shows it, as the runner names it (macros/runner.py `choosing`).
            read, chosen = run.read, []

            def first() -> World:
                world = read()
                if not chosen and world.player is not None:
                    chosen.append(True)
                    run.build = warlock(world)
                return world

            run.read = first
        if self.hover_known:
            run.hovered = self.unit_under_pointer
        run.things = lambda: () if self.thing is None else (self.thing,)
        run.containers = run.things
        run.keys = dict(KEYS)
        run.prebuff_hands = frozenset(PREBUFF_SET)
        run.battle_hands = frozenset(PREBUFF_SET)
        return run

    def read(self) -> World:
        here = self.world.player
        if here is not None and any(d.kind == 'gold' for d in self.loot.drops):  # gold is taken by standing on it
            on = [
                d
                for d in self.loot.drops
                if d.kind == 'gold' and math.dist((d.x, d.y), (here.x, here.y)) < self.gold_radius
            ]
            self.picked += [d.label for d in on]
            self.loot = replace(self.loot, drops=tuple(d for d in self.loot.drops if d not in on))
        if self.loaded_at is not None and self.clock.now >= self.loaded_at:
            self.deaf, self.loaded, self.loaded_at = False, self.loaded_at, None
            self.world = replace(self.world, view=254)
        while self.arrivals and self.clock.now >= self.arrivals[0][0]:
            self.arrivals.pop(0)[1]()
        if self.acting_until is not None and self.clock.now >= self.acting_until and self.kept_hop:
            self.kept_hop = False  # the key kept during the cast: cast now, no neutral frame shown
            self.hop()
            self.hops_cast_at.append(self.clock.now)
            self.acting_until = self.clock.now + ACTING_SECONDS
        elif self.acting_until is not None and self.clock.now >= self.acting_until and self.kept:
            self.acting_until = None
            event = self.kept.pop(0)
            self.act(event)  # the key kept during the cast: its own cast begins, no neutral frame shown
            self.acting_until = self.clock.now + ACTING_SECONDS
            # Quick Cast: the key's skill is on the right button for its cast, the one before after it.
            name = event[1] if event[0] == 'key' else f'Button{event[1]}'
            cast = next((skill for skill, key in KEYS.items() if key == name), None)
            if self.home_skill is None:
                self.home_skill = (self.character.right_skill,)
            self.world = replace(self.world, player=replace(self.character, mode=7, right_skill=cast))
        elif self.acting_until is not None and self.clock.now >= self.acting_until:
            self.acting_until = None  # one neutral frame between casts
            if self.home_skill is not None:
                self.world = replace(self.world, player=replace(self.character, right_skill=self.home_skill[0]))
                self.home_skill = None
            self.world = replace(self.world, player=replace(self.character, mode=5))
        elif self.acting_until is None and self.world.in_game and not self.deaf and not self.reading:
            held = self.held_input()
            if held and (self.repeats or self.struck_hold != self.keys.hold_serial):
                self.struck_hold = self.keys.hold_serial
                self.reading = True
                try:
                    self.keys.on_event(('held', held))
                finally:
                    self.reading = False
        return self.world

    def pressed(self) -> list[str]:
        return [event[1] for event in self.keys.events if event[0] == 'key']
