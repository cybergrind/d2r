"""A scripted game for macro tests: a fake X connection and a world that reacts to its events."""

import math
import random
from dataclasses import replace

from inventory_tracking.macros.actuator import Actuator
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import (
    CONSUME,
    DEATH_MARK,
    ECHOING_STRIKE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SIGIL_LETHARGY,
    SUMMON_DEFILER,
    SWAP_WEAPONS,
    TELEPORT,
)
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import Loot, Monster, Player, Teleport, World


KEYS = {SUMMON_DEFILER: 'q', CONSUME: '6', HEX_PURGE: 'g', PSYCHIC_WARD: 'r', SWAP_WEAPONS: 'c', TELEPORT: 't'}
KEYS[SIGIL_LETHARGY] = 'Button9'  # mouse 5, as CybergrindAA's key file
KEYS[ECHOING_STRIKE] = '7'  # bound by the user on 2026-10-09 so Quick Cast aims it with the pointer
KEYS[DEATH_MARK] = 'd'
STRIKE_RANGE = 4.0  # world units: a monster this near the blades' line to the pointer is struck
ACTING_SECONDS = 0.3  # the cast animation
PREBUFF_SET, OTHER_SET = ('fla', 'uit'), ('6cs', 'wa3')  # Heart of the Oak + Spirit; Naj's Puzzler + Codex
SLOTS = (379, 390, 375, 384, 389, 220, 393, 377, None, 382, 387, 54, 381, None, None, None)
HUNT_SLOTS = (*SLOTS[:13], ECHOING_STRIKE, *SLOTS[14:])  # with Echoing Strike on a key, as since 2026-10-09
WINDOW = (1920, 0, 2560, 1418)


class FakeConnection:
    """Records events as ('key', name), ('move', x, y) and ('click',); `on_event` may react."""

    def __init__(self):
        self.events = []
        self.down = []
        self.buttons_down = set()
        self.hold_serial = 0  # counts presses of keys and buttons: a game casting once per press looks at it
        self.held = False
        self.at = (2500, 900)
        self.names = {}
        self.shift = False  # Shift was down at the last left click
        self.on_event = lambda event: None

    def keycodes(self, names):
        codes = []
        for name in names:
            text = name.decode()
            if text == 'unknown':
                return None
            self.names.setdefault(text, len(self.names) + 10)
            codes.append(self.names[text])
        return codes

    def any_key_held(self):
        return bool(self.held_keys())

    def held_keys(self):
        """`held`: True for some key of the player's, or the names of the keys that are down."""
        other = {1} if self.held is True else {self.keycodes([name.encode()])[0] for name in self.held or ()}
        return frozenset(self.down) | other

    def focused_window_pid(self):
        return 1

    def focused_window_rect(self):
        return WINDOW

    def pointer(self):
        return self.at

    def pointer_state(self):
        return (*self.at, 0)

    def move_pointer(self, x, y):
        self.at = (x, y)
        return True

    def _emit(self, event):
        self.events.append(event)
        self.on_event(event)

    def press(self, code):
        self.down.append(code)
        self.hold_serial += 1
        return True

    def down_names(self):
        return {name for name, value in self.names.items() if value in self.down}

    def release(self, code):
        if code in self.down:
            self.down.remove(code)
            self._emit(('key', next(name for name, value in self.names.items() if value == code)))
        return True

    def button(self, button, down):
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

    def sync(self):
        pass

    def fraction(self):
        return (self.at[0] - WINDOW[0]) / WINDOW[2], (self.at[1] - WINDOW[1]) / WINDOW[3]


NPC = Monster(7, 513, 1, 5010.0, 5010.0, 0xFFFFFFFF)  # a town resident


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def player(area=109, **changes):
    return replace(Player(1, 'CybergrindAA', 5, area, 5000.0, 5000.0, False), **changes)


def world(area=109, **changes):
    return replace(World(True, (), 'cyber32', SLOTS, player=player(area)), **changes)


class Game:
    """A world that changes the way the game does when the macro's events arrive."""

    def __init__(self, start: World):
        self.world = start
        self.keys = FakeConnection()
        self.keys.on_event = self.react
        self.clock = Clock()
        self.focused = True
        self.said = []
        self.next_unit = 100
        self.consume_takes = None  # unit id Consume removes instead of the Defiler aimed at
        self.field_focused = False
        self.sets = [PREBUFF_SET, OTHER_SET]  # the first is in hand
        self.loading_seconds = 6.0
        self.view_marks = True  # the view byte goes to 0 while the game loads
        self.ignored = []
        self.deaf = False  # the loading screen: the game exists and takes no input
        self.loaded_at = None
        self.loaded = 0.0  # when the game came up
        self.blocked = lambda x, y: False  # window fractions where a summon cannot stand
        self.deaf_clicks = 0  # clicks the lobby ignores while it is still coming up
        self.staff: Teleport | None = None  # the worn Teleport staff; None: Teleport as a skill, if in a slot
        self.door: tuple[float, float] | None = None  # a warp, in tiles: a click near it walks the character in
        self.door_above = 0.0  # classic pixels (600 high) the door is clicked above its tile; 0: on the ground
        self.next_area = 110
        self.sigils = []  # ground points Sigil: Lethargy was cast at
        self.strikes = []  # (unit id or None, ground point) per Shift+click
        self.toughness = {}  # unit id -> strikes it survives (default: dies to the first)
        self.acting_until = None  # the cast animation: the player's mode is 7 until then
        self.arrivals = []  # (clock time, callable): what happens in the game on its own, in time order
        self.marks = []  # unit ids Death Mark was cast on (the monster nearest the pointer), or None
        self.walks = []  # ground points clicked in a game: the character walks there at once
        self.repeats = True  # a held skill input casts again and again (the game); False: once per press
        self.struck_hold = None  # the press the last cast came from (hold_serial)
        self.reading = False
        self.loot = Loot()  # the drops, the belt and the life (the pickup step); a click on a drop's ground picks it up
        self.picked = []  # labels of the drops picked up
        self.hover_known = True  # the game's record of the unit under the pointer can be read
        self.deaf_picks = 0  # clicks on a drop the game takes nothing from (a cast was ending)
        self.pick_above = 14.0  # classic pixels a drop is clicked above its ground (host, 2026-10-10)
        self.label_above = {}  # unit id -> the same for one drop: a pile shifts its labels (host, 21:10)
        self.belt_after = {}  # drops picked up so far -> the belt from then on (a potion lands in it)

    def react(self, event):
        self.read()
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
            elif key == 't':
                charged = self.staff is not None and self.staff.in_hand and self.staff.charges > 0
                if charged or (self.staff is None and 54 in w.slots):
                    x, y = self.ground_under_pointer()
                    self.world = replace(w, player=replace(w.player, x=x, y=y))
                    if self.staff is not None:
                        self.staff = replace(self.staff, charges=self.staff.charges - 1)
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
                buffed = bool(w.player.consume) and len(kept) == len(w.monsters)
                self.world = replace(
                    w,
                    monsters=(*kept, Monster(self.next_unit, 744, 1, x, y, 0xFFFFFFFF)),
                    player=replace(w.player, consume=buffed),
                )
            elif key == '6':
                hit = self.consume_takes or self.pet_under_pointer()
                if hit is not None:
                    left = tuple(m for m in w.monsters if m.unit_id != hit)
                    self.world = replace(w, monsters=left, player=replace(w.player, consume=True))
        elif event[0] == 'button' and event[1] == 9 and w.in_game:
            self.sigils.append(self.ground_under_pointer())
        elif event[0] == 'held':  # a skill input down while the character is free: the game casts it
            if event[1] in ('7', 'Button3') or w.player.left_skill == ECHOING_STRIKE:
                self.strike()
            else:  # the plain attack, in place: an animation and nothing hit (host, 20:07 on 2026-10-09)
                self.world = replace(w, player=replace(w.player, mode=7))
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
            elif w.in_game:
                gx, gy = self.ground_under_pointer()
                door = None if self.door is None else (self.door[0] * 5, self.door[1] * 5)
                lift = self.door_above / 16  # a pixel down the screen is 1/16 of a unit along both axes
                if (
                    door
                    and math.dist((gx + lift, gy + lift), door) < 5
                    and math.dist((w.player.x, w.player.y), door) < 30
                ):
                    self.world = replace(w, player=replace(w.player, area=self.next_area, x=door[0], y=door[1]))
                elif (drop := self.drop_under_pointer()) is not None and self.deaf_picks:
                    self.deaf_picks -= 1
                elif drop is not None:
                    self.picked.append(drop.label)
                    self.loot = replace(self.loot, drops=tuple(d for d in self.loot.drops if d is not drop))
                    if len(self.picked) in self.belt_after:
                        self.loot = replace(self.loot, belt=self.belt_after[len(self.picked)])
                    self.world = replace(w, player=replace(w.player, x=drop.x, y=drop.y))
                elif math.dist((gx, gy), (w.player.x, w.player.y)) < 40:  # a click on the ground: a walk there
                    self.walks.append((gx, gy))
                    self.world = replace(w, player=replace(w.player, x=gx, y=gy))

    def drop_under_pointer(self):
        """The drop whose ground the pointer is on (`pick_above` pixels above it), within a walk."""
        gx, gy = self.ground_under_pointer()
        player = self.world.player
        for drop in self.loot.drops:
            lift = self.label_above.get(drop.unit_id, self.pick_above) / 16
            near = math.dist((gx + lift, gy + lift), (drop.x, drop.y)) < 0.5
            if near and math.dist((player.x, player.y), (drop.x, drop.y)) < 40:
                return drop
        return None

    def held_input(self):
        """The Echoing Strike input held right now, as `react` names it, or None."""
        w, keys = self.world, self.keys
        if '7' in keys.down_names() and ECHOING_STRIKE in w.slots:
            return '7'
        if 3 in keys.buttons_down and w.player.right_skill == ECHOING_STRIKE:
            return 'Button3'
        if 1 in keys.buttons_down and 'Shift_L' in keys.down_names():
            return 'Shift+click'
        return None

    def strike(self):
        """Echoing Strike toward the pointer: the blades fly from the character to the ground under it
        and meet there; the hostile nearest their line, within STRIKE_RANGE of it, takes a hit."""
        w = self.world
        x, y = self.ground_under_pointer()
        p = (w.player.x, w.player.y)

        def off_line(m):
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
            if left <= 0:
                monsters = tuple(m for m in monsters if m.unit_id != hit.unit_id)
                dead = dead | {hit.unit_id}  # it lies there: a kill, not a unit that only left memory
        self.world = replace(w, monsters=monsters, dead=dead, player=replace(w.player, mode=7))
        self.acting_until = self.clock.now + ACTING_SECONDS

    def under_pointer(self):
        """World position drawn under the pointer (the inverse of routines.screen_fraction)."""
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        a = (fx - 0.5) * aspect * 600 / 16
        b = (fy - 0.494 + 0.035) * 600 / 8
        p = self.world.player
        return p.x + (a + b) / 2, p.y + (b - a) / 2

    def ground_under_pointer(self):
        """World position of the ground under the pointer (the inverse of teleport.ground_fraction)."""
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        a = (fx - 0.5) * aspect * 600 / 16
        b = (fy - 0.494) * 600 / 8
        p = self.world.player
        return p.x + (a + b) / 2, p.y + (b - a) / 2

    def pet_under_pointer(self):
        """Consume takes the demon nearest the pointer, the bound one as readily as a Defiler."""
        x, y = self.under_pointer()
        # The bound demon is tall: drawn below the pointer, its body still covers it (host, 2026-10-07).
        for m in self.world.monsters:
            across, down = (m.x - m.y) - (x - y), (m.x + m.y) - (x + y)
            if m.txt_id == 700 and abs(across) < 6 and 0 <= down < 18:
                return m.unit_id
        near = [m for m in self.world.monsters if m.txt_id in (744, 700) and math.hypot(m.x - x, m.y - y) < 5]
        return min(near, key=lambda m: math.hypot(m.x - x, m.y - y)).unit_id if near else None

    def run(self, seed=1) -> Run:
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
        )
        if self.hover_known:
            run.hovered = lambda: (4, drop.unit_id) if (drop := self.drop_under_pointer()) else (0, 0)
        run.keys = dict(KEYS)
        run.prebuff_hands = frozenset(PREBUFF_SET)
        run.battle_hands = frozenset(PREBUFF_SET)
        return run

    def read(self):
        if self.loaded_at is not None and self.clock.now >= self.loaded_at:
            self.deaf, self.loaded, self.loaded_at = False, self.loaded_at, None
            self.world = replace(self.world, view=254)
        while self.arrivals and self.clock.now >= self.arrivals[0][0]:
            self.arrivals.pop(0)[1]()
        if self.acting_until is not None and self.clock.now >= self.acting_until:
            self.acting_until = None  # one neutral frame between casts
            self.world = replace(self.world, player=replace(self.world.player, mode=5))
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

    def pressed(self):
        return [event[1] for event in self.keys.events if event[0] == 'key']
