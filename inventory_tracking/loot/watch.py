"""Show valuable runes on the ground, wanted shrines and super chests (streamed, often off-screen)
as HUD arrow rows.

Polled from `serve` like the level guide: never waits for the capture lock, reads only when
D2R is focused, logs each new rune once, and clears the card when nothing is in range.
"""

import math
import threading

from inventory_tracking.common import LOG
from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.levels.guide import pointer_lines
from inventory_tracking.loot.ground import observe_ground
from inventory_tracking.loot.runes import rune_name


class RuneWatcher:
    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        focused,
        display,
        poll_interval,
        minimum: str,
        shrine_types: frozenset[int] = frozenset(),
        super_chests: bool = True,
        observe=observe_ground,
    ):
        self.source, self.capture_lock, self.focused, self.display = source, capture_lock, focused, display
        self.poll_interval, self.minimum, self.observe = poll_interval, minimum, observe
        self.shrine_types, self.super_chests = shrine_types, super_chests
        self.last_poll = -math.inf
        self.visible = []
        self.seen: set[int] = set()
        self.last_warning = None

    def poll(self, now):
        if now - self.last_poll < self.poll_interval or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            self.source.ensure_connected()
            if not self.focused(self.source.images):
                self.visible = []
                return
            location, runes, marks = self.observe(
                self.source.pid,
                self.source.images,
                self.source.capture,
                minimum=self.minimum,
                shrine_types=self.shrine_types,
                super_chests=self.super_chests,
            )
        except Exception as exc:
            text = f'Rune watch: read failed: {exc}'
            if text != self.last_warning:
                LOG.warning('%s', text)
                self.last_warning = text
            return
        finally:
            self.capture_lock.release()
        for rune in runes:
            if rune.unit_id not in self.seen:
                LOG.info('Ground rune: %s at (%s, %s)', rune_name(rune.class_id), rune.x, rune.y)
        for mark in marks:
            if mark.unit_id not in self.seen:
                LOG.info('Loot mark: %s at (%s, %s)', mark.label, mark.x, mark.y)
        self.seen = {rune.unit_id for rune in runes} | {mark.unit_id for mark in marks}
        if location is None:
            self.visible = []
            return
        ordered = sorted(runes, key=lambda rune: -rune.class_id)  # highest rune first
        self.visible = pointer_lines(
            [Pointer(m.label, None, m.x - location.x, m.y - location.y) for m in marks]
            + [Pointer(rune_name(r.class_id), None, r.x - location.x, r.y - location.y) for r in ordered]
        )

    def tick(self):
        self.display(self.visible if self.focused(self.source.images) else [])
