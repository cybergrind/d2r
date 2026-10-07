"""A scripted game for macro tests: a fake X connection and a world that reacts to its events."""

import math
import random
from dataclasses import replace

from inventory_tracking.macros.actuator import Actuator
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import CONSUME, HEX_PURGE, PSYCHIC_WARD, SUMMON_DEFILER, SWAP_WEAPONS
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import Monster, Player, World


KEYS = {SUMMON_DEFILER: 'q', CONSUME: '6', HEX_PURGE: 'g', PSYCHIC_WARD: 'r', SWAP_WEAPONS: 'c'}
PREBUFF_SET, OTHER_SET = ('fla', 'uit'), ('6cs', 'wa3')  # Heart of the Oak + Spirit; Naj's Puzzler + Codex
SLOTS = (379, 390, 375, 384, 389, 220, 393, 377, None, 382, 387, 54, 381, None, None, None)
WINDOW = (1920, 0, 2560, 1418)


class FakeConnection:
    """Records events as ('key', name), ('move', x, y) and ('click',); `on_event` may react."""

    def __init__(self):
        self.events = []
        self.down = []
        self.held = False
        self.at = (2500, 900)
        self.names = {}
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
        return self.held or bool(self.down)

    def focused_window_pid(self):
        return 1

    def focused_window_rect(self):
        return WINDOW

    def pointer(self):
        return self.at

    def move_pointer(self, x, y):
        self.at = (x, y)
        return True

    def _emit(self, event):
        self.events.append(event)
        self.on_event(event)

    def press(self, code):
        self.down.append(code)
        return True

    def release(self, code):
        if code in self.down:
            self.down.remove(code)
            self._emit(('key', next(name for name, value in self.names.items() if value == code)))
        return True

    def button(self, button, down):
        if not down:
            self._emit(('click', self.fraction()))
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
        elif event[0] == 'click':
            x, y = event[1]
            if w.quit_menu and abs(x - 0.5) < 0.08 and abs(y - 0.438) < 0.02:
                self.world = World(False, (), w.game_name, w.slots)
            elif not w.in_game and 0.67 < x < 0.85 and abs(y - 0.158) < 0.011:
                if self.deaf_clicks:
                    self.deaf_clicks -= 1
                else:
                    self.field_focused = True

    def under_pointer(self):
        """World position drawn under the pointer (the inverse of routines.screen_fraction)."""
        fx, fy = self.keys.fraction()
        aspect = WINDOW[2] / WINDOW[3]
        a = (fx - 0.5) * aspect * 600 / 16
        b = (fy - 0.494 + 0.035) * 600 / 8
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
        )
        run.keys = dict(KEYS)
        run.prebuff_hands = frozenset(PREBUFF_SET)
        return run

    def read(self):
        if self.loaded_at is not None and self.clock.now >= self.loaded_at:
            self.deaf, self.loaded, self.loaded_at = False, self.loaded_at, None
            self.world = replace(self.world, view=254)
        return self.world

    def pressed(self):
        return [event[1] for event in self.keys.events if event[0] == 'key']
