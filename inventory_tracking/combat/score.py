"""The live scorer (combat/plan.md stage 6): what the play is worth right now, from the game's memory.

`LiveScore.note` takes each world read while attack mode runs and keeps the last WINDOW seconds: the hostiles'
life points lost (every source counts), the kills (a hostile once within COMBAT_REACH now lying dead: the
recorder's `kill`), the hostiles only gone (the recorder's `gone`, worth nothing) and the combat seconds. A new
level or unit drops what is known. `line` is the HUD card's text: damage per combat second and kills per minute.
"""

import math
from collections import deque
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.tables import points_of


WINDOW = 60.0  # seconds the score looks back
COMBAT_REACH = 30.0  # world units: a second with a live hostile this near is a combat second
GAP = 0.5  # seconds: two reads further apart than this are not one stretch of play (a pause, a loading screen)


@dataclass
class LiveScore:
    window: float = WINDOW
    # clock, combat seconds, points, kills, gone
    samples: deque[tuple[float, float, float, int, int]] = field(default_factory=deque)
    life: dict[int, tuple[float, float, bool]] = field(default_factory=dict)  # unit -> (points left, full, near)
    last: float | None = None
    place: tuple[int, int] | None = None  # (the character's unit id, its level) at the last read
    killed: int = 0  # every kill counted since made, never dropped (macros/loop.py `still`: a stand that kills)

    def note(self, clock: float, player: Any, hostiles: Iterable[Any], dead: Collection[int] = ()) -> None:
        """One read: `player` and `hostiles` are game/records.py records (None: not in a game), `dead`
        the unit ids of the monsters lying dead (World.dead)."""
        if player is None:
            self.life, self.last, self.place = {}, None, None
            return
        place = (player.unit_id, player.area)
        if place != self.place:
            self.life, self.last, self.place = {}, None, place  # another level or game: nothing carries over
        here = (player.x, player.y)
        now: dict[int, tuple[float, float, bool]] = {}
        points = 0.0
        for m in hostiles:
            full = points_of(m.txt_id, player.area)
            left = full * (m.life / m.max_life if m.max_life else 1.0)
            near = math.dist(here, (m.x, m.y)) <= COMBAT_REACH
            now[m.unit_id] = (left, full, near)
            before = self.life.get(m.unit_id)
            if before is not None and left < before[0]:
                points += before[0] - left
        kills = gone = 0
        for unit, (left, _full, near) in self.life.items():
            if unit in now or not near:
                continue
            if unit in dead:
                kills += 1
                points += left
            else:
                gone += 1
        elapsed = clock - self.last if self.last is not None else 0.0
        steady = 0.0 < elapsed <= GAP
        combat = elapsed if steady and any(near for _, _, near in self.life.values()) else 0.0
        self.killed += kills
        if steady:
            self.samples.append((clock, combat, points, kills, gone))
        self.life, self.last = now, clock
        while self.samples and clock - self.samples[0][0] > self.window:
            self.samples.popleft()

    def totals(self) -> dict[str, float]:
        seconds = sum(sample[1] for sample in self.samples)
        points = sum(sample[2] for sample in self.samples)
        kills = sum(sample[3] for sample in self.samples)
        return {
            'combat_seconds': round(seconds, 1),
            'points': round(points),
            'kills': kills,
            'gone': sum(sample[4] for sample in self.samples),
            'points_per_combat_second': round(points / seconds) if seconds else 0,
            'kills_per_minute': round(kills / seconds * 60, 1) if seconds else 0.0,
        }

    def line(self) -> str:
        found = self.totals()
        if not found['combat_seconds']:
            return 'no combat yet'
        return (
            f'{found["points_per_combat_second"]} points/s, {found["kills_per_minute"]:g} kills/min '
            f'over {found["combat_seconds"]:g}s of combat'
        )
