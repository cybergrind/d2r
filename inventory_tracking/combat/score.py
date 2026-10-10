"""The live scorer (combat/plan.md stage 6): what the play is worth right now, from the game's memory.

`LiveScore.note` takes each read of the world while attack mode runs (macros/hunt.py hands them
over) and keeps the last WINDOW seconds:

- the life points the hostiles lost between two reads (a monster's type and area give its points, the
  client its life fraction; every source counts, the companions' too);
- the kills: a hostile that was within COMBAT_REACH and is now among the dead the game holds
  (`dead`, the unit ids lying in a dead mode), with the life it had left. This is the recorder's
  `kill` event (combat/record.py);
- the hostiles only gone: no longer in memory and not seen dead (the character teleported away, the
  monster left the streamed area). The recorder's `gone`: counted beside the kills, worth nothing;
- the combat seconds: an interval is combat when a live hostile was within COMBAT_REACH at its start,
  so the interval a pack's last monster dies in counts.

What is known of the monsters is dropped when the character is in another level or is another unit
(a new game reuses unit ids). `line` is the HUD card's text: effective damage per combat second and
kills per minute over the window.
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

    def note(self, clock: float, player: Any, hostiles: Iterable[Any], dead: Collection[int] = ()) -> None:
        """One read: `player` and `hostiles` are macros/world.py records (None: not in a game), `dead`
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
