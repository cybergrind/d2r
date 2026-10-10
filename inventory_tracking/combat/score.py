"""The live scorer (combat/plan.md stage 6): what the play is worth right now, from the game's memory.

`LiveScore.note` takes each read of the world while attack mode runs (macros/hunt.py hands them
over) and keeps the last WINDOW seconds: the life points the hostiles lost (a monster's type and area
give its points, the client its life fraction; every source counts, the companions' too), the kills
(a hostile gone from memory while within COMBAT_REACH), and the combat seconds (a live hostile within
COMBAT_REACH, the definition analysis.py and the simulator use). `line` is the HUD card's text:
effective damage per combat second and kills per minute over the window.
"""

import math
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.tables import points_of


WINDOW = 60.0  # seconds the score looks back
COMBAT_REACH = 30.0  # world units: a second with a live hostile this near is a combat second
GAP = 0.5  # seconds: two reads further apart than this are not one stretch of play (a pause, a loading screen)


@dataclass
class LiveScore:
    window: float = WINDOW
    samples: deque[tuple[float, float, float, int]] = field(default_factory=deque)  # clock, seconds, points, kills
    life: dict[int, tuple[float, float, bool]] = field(default_factory=dict)  # unit -> (points left, full, near)
    last: float | None = None

    def note(self, clock: float, player: Any, hostiles: Iterable[Any]) -> None:
        """One read: `player` and `hostiles` are macros/world.py records (None: not in a game)."""
        if player is None:
            self.life, self.last = {}, None
            return
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
        kills = 0
        for unit, (left, _full, near) in self.life.items():
            if unit not in now and near:
                kills += 1
                points += left
        elapsed = clock - self.last if self.last is not None else 0.0
        steady = 0.0 < elapsed <= GAP
        combat = elapsed if steady and any(near for _, _, near in now.values()) else 0.0
        if steady:
            self.samples.append((clock, combat, points, kills))
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
