"""The damage a character takes, measured the same way in a take and in an arena play, for calibrating a situation cut
from the take (rca/2026-10-21/fane-death-sim-findings.md §2: "compare the arena's damage intake with the take's, at
matched moments").

Over a window, by monster type:

- `close`: monster-seconds within CLOSE (3 units) of the character, alive and hostile;
- `swings`: the attacks begun within REACH (4 units) of the character: in a take a monster's mode turning to an attack
  (monmode A1, A2: ATTACK_MODES), in a play a walker's swing at the character begun (a new landing frame, `Sampler`);
- `blows` and `lost`: the life taken. In a take each `hurt` event is put on its nearest attacker within REACH (the
  event's `by`, nearest first) and counts one blow (a frame can hold two: a lower bound); in a play each blow is
  stage.py `Hurt`;
- `engaged`: the mean length of a monster's stays within CLOSE.

The rates follow: swings a close-second, life a close-second, blows a swing (the share that lands: the hit chance
against the character's defence and block, and the swings a stagger cut short, together).
"""

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.sim.monsters import MELEE, STRIKE
from inventory_tracking.takes.takes import Take, monsters_of, player_of
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of


CLOSE = 3.0  # units: in melee (the takes' blows came from 1.2-3.6)
REACH = 4.0  # units: an attack begun this near is on the character
ATTACK_MODES = frozenset((4, 5))  # monmode A1, A2


@dataclass
class Intake:
    """The window's measures by monster type (the module text)."""

    seconds: float = 0.0
    close: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    swings: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    blows: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    lost: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    stays: dict[int, list[float]] = field(default_factory=lambda: defaultdict(list))
    unplaced: float = 0.0  # life lost with no attacker within REACH (a blast, a missile)

    def add(self, other: Intake) -> None:
        self.seconds += other.seconds
        self.unplaced += other.unplaced
        for name in ('close', 'swings', 'blows', 'lost'):
            mine = getattr(self, name)
            for txt, value in getattr(other, name).items():
                mine[txt] += value
        for txt, stays in other.stays.items():
            self.stays[txt] += stays

    def row(self, txt: int, plays: int = 1) -> dict[str, float | str]:
        close = self.close.get(txt, 0.0)
        swings, blows, lost = self.swings.get(txt, 0), self.blows.get(txt, 0), self.lost.get(txt, 0.0)
        stays = self.stays.get(txt, [])
        return {
            'type': name_of(txt),
            'close s': round(close / plays, 2),
            'swings/close s': round(swings / close, 2) if close else math.nan,
            'blows/swing': round(blows / swings, 2) if swings else math.nan,
            'life/close s': round(lost / close) if close else math.nan,
            'life a play': round(lost / plays),
            'engaged s': round(sum(stays) / len(stays), 2) if stays else math.nan,
        }

    def total(self, plays: int = 1) -> dict[str, float]:
        close = sum(self.close.values())
        lost = sum(self.lost.values()) + self.unplaced
        return {
            'close s': round(close / plays, 2),
            'life a play': round(lost / plays),
            'life/s': round(lost / self.seconds) if self.seconds else math.nan,
            'life/close s': round(sum(self.lost.values()) / close) if close else math.nan,
            'swings/close s': round(sum(self.swings.values()) / close, 2) if close else math.nan,
            'blows/swing': round(sum(self.blows.values()) / sum(self.swings.values()), 2)
            if sum(self.swings.values())
            else math.nan,
        }


class Stays:
    """Each monster's stays within CLOSE, as frames or ticks come."""

    def __init__(self) -> None:
        self.since: dict[int, tuple[int, float]] = {}

    def step(self, at: float, near: Mapping[int, int], intake: Intake) -> None:
        for unit, txt in near.items():
            self.since.setdefault(unit, (txt, at))
        for unit in [unit for unit in self.since if unit not in near]:
            txt, began = self.since.pop(unit)
            intake.stays[txt].append(at - began)

    def end(self, at: float, intake: Intake) -> None:
        self.step(at, {}, intake)


def of_take(take: Take, start: float, seconds: float) -> Intake:
    """The window of `seconds` from `start` (the take's clock) of a take."""
    found, stays = Intake(seconds=0.0), Stays()
    end = start + seconds
    modes: dict[int, int] = {}
    last: float | None = None
    for frame in take.frames:
        at = frame['t']
        if at < start:
            for monster in monsters_of(frame):
                modes[monster.unit] = monster.mode
            continue
        if at > end:
            break
        player = player_of(frame)
        if player is None or not player.life:
            break
        dt = 0.0 if last is None else at - last
        last = at
        found.seconds += dt
        near: dict[int, int] = {}
        for monster in monsters_of(frame):
            if not monster.hostile:
                continue
            away = math.dist(monster.at, player.at)
            if away <= CLOSE:
                found.close[monster.txt] += dt
                near[monster.unit] = monster.txt
            if away <= REACH and monster.mode in ATTACK_MODES and modes.get(monster.unit) not in ATTACK_MODES:
                found.swings[monster.txt] += 1
            modes[monster.unit] = monster.mode
        stays.step(at, near, found)
    stays.end(last or start, found)
    for event in take.events:
        if event.get('event') != 'hurt' or not start < event['t'] <= end:
            continue
        by = [row for row in event.get('by', ()) if len(row) > 4 and row[4] <= REACH]
        if by:
            txt = min(by, key=lambda row: row[4])[1]
            found.blows[txt] += 1
            found.lost[txt] += event.get('lost', 0)
        else:
            found.unplaced += event.get('lost', 0)
    return found


class Sampler:
    """An `each_tick` for `Situation.play` that measures a play as `of_take` measures a take, up to `seconds`."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.found = Intake()
        self.stays = Stays()
        self.lands: dict[int, int] = {}
        self.last: float | None = None
        self.hurts = 0

    def __call__(self, stage: Any, play: Any) -> None:
        now = stage.clock.now
        if now > self.seconds or stage.over is not None:
            return
        dt = 0.0 if self.last is None else now - self.last
        self.last = now
        found = self.found
        found.seconds += dt
        here = stage.here
        mobs = stage.mobs
        near: dict[int, int] = {}
        for unit in mobs.live():
            mob = mobs.mobs[unit]
            away = math.dist(mob.at, here)
            if away <= CLOSE:
                found.close[mob.txt] += dt
                near[unit] = mob.txt
            walker = mobs.pack.walkers.get(unit)
            if walker is None:
                continue
            # A swing begun: its landing frame set anew (a walker may swing again without leaving STRIKE)
            if walker.doing == STRIKE and walker.lands != self.lands.get(unit) and walker.aim == 0 and away <= REACH:
                found.swings[mob.txt] += 1
            self.lands[unit] = walker.lands
        self.stays.step(now, near, found)
        hurts = stage.cast.hurts
        for hurt in hurts[self.hurts :]:
            if hurt.kind == MELEE:
                found.blows[hurt.txt] += 1
                found.lost[hurt.txt] += hurt.points
            else:
                found.unplaced += hurt.points
        self.hurts = len(hurts)

    def close(self) -> Intake:
        self.stays.end(self.last or 0.0, self.found)
        return self.found


def table(rows: Sequence[tuple[str, Intake, int]], types: Sequence[int]) -> list[str]:
    """Markdown rows: each (label, intake, plays) by type and in all."""
    head = '| source | type | close s | swings/close s | blows/swing | life/close s | life a play | engaged s |'
    lines = [head, '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for label, intake, plays in rows:
        for txt in types:
            row = intake.row(txt, plays)
            lines.append(f'| {label} | ' + ' | '.join(str(value) for value in row.values()) + ' |')
        total = intake.total(plays)
        lines.append(
            f'| {label} | all | {total["close s"]} | {total["swings/close s"]} | {total["blows/swing"]} | '
            f'{total["life/close s"]} | {total["life a play"]} | - |'
        )
    return lines
