"""Reading takes written by combat/record.py: the frames, events and units of one stay in a level."""

import gzip
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from inventory_tracking.macros.routines import world_point
from inventory_tracking.macros.world import LEADER_FLAGS, MINION_FLAG, NO_OWNER, Player
from inventory_tracking.native.layout import DEAD_MODES


Point = tuple[float, float]
LIFE_SCALE = 128  # the client's life fraction: a monster's life in a frame is 0-128 of its maximum


class PlayerRow(NamedTuple):
    """The character in a frame (`p`); the vitals are there since 2026-10-10 (whole points)."""

    unit: int
    mode: int
    area: int
    x: float
    y: float
    left_skill: int | None = None
    right_skill: int | None = None
    life: int | None = None
    max_life: int | None = None
    mana: int | None = None
    max_mana: int | None = None

    @property
    def at(self) -> Point:
        return (self.x, self.y)


class MonsterRow(NamedTuple):
    """One monster in a frame (`m`), dead ones included."""

    unit: int
    txt: int
    mode: int
    x: float
    y: float
    life: int
    max_life: int
    flags: int
    owner: int
    ally: int

    @property
    def at(self) -> Point:
        return (self.x, self.y)

    @property
    def alive(self) -> bool:
        return self.mode not in DEAD_MODES

    @property
    def hostile(self) -> bool:
        """Alive, not owned and not allied: what the blades are for."""
        return self.alive and self.owner == NO_OWNER and not self.ally

    @property
    def companion(self) -> bool:
        """Alive and the character's own: the mercenary or a pet."""
        return self.alive and bool(self.ally or self.owner != NO_OWNER)

    @property
    def elite(self) -> bool:
        return bool(self.flags & LEADER_FLAGS) and not self.flags & MINION_FLAG

    @property
    def life_share(self) -> float:
        """The share of its life the client shows (1.0 when the stats were unread)."""
        return self.life / self.max_life if self.max_life else 1.0


class MissileRow(NamedTuple):
    """One missile in a frame (`x`): `path` is its path record's first bytes, hex."""

    unit: int
    txt: int
    mode: int
    x: float
    y: float
    path: str


def player_of(frame: dict[str, Any]) -> PlayerRow | None:
    return PlayerRow(*frame['p']) if frame.get('p') else None


def monsters_of(frame: dict[str, Any]) -> list[MonsterRow]:
    return [MonsterRow(*m) for m in frame['m']]


def missiles_of(frame: dict[str, Any]) -> list[MissileRow]:
    return [MissileRow(*x) for x in frame['x']]


def pointer_of(frame: dict[str, Any]) -> Point | None:
    """The pointer in window fractions (`in`: root x, y, button mask, fraction x, y, keys down)."""
    fx, fy = frame['in'][3], frame['in'][4]
    return None if fx is None else (fx, fy)


def ground_under_pointer(frame: dict[str, Any], aspect: float, lift: float = 0.0) -> Point | None:
    """The world point drawn under the frame's pointer (`lift` window fractions lower: a body's feet);
    None without the character or the pointer."""
    player, pointer = player_of(frame), pointer_of(frame)
    if player is None or pointer is None:
        return None
    stand = Player(player.unit, '', player.mode, player.area, player.x, player.y, None)
    return world_point(stand, pointer[0], pointer[1] + lift, aspect)


def lines(path: Path) -> Iterator[dict[str, Any]]:
    """The records of a JSON lines file, or of its gzip beside it (`trim` writes those: test fixtures)."""
    packed = path.with_name(path.name + '.gz')
    if not path.exists() and not packed.exists():
        return
    with path.open(encoding='utf-8') if path.exists() else gzip.open(packed, 'rt', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


RECORDING_NAME = re.compile(r'\d{8}T\d{6}Z-\d+')  # a recorder's directory: start time and area


@dataclass
class Take:
    directory: Path
    manifest: dict[str, Any]
    frames: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    units: list[dict[str, Any]] = field(default_factory=list)
    missiles: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, directory: Path) -> Take:
        manifest = json.loads((directory / 'manifest.json').read_text())
        return cls(
            directory,
            manifest,
            list(lines(directory / 'frames.jsonl')),
            list(lines(directory / 'events.jsonl')),
            list(lines(directory / 'units.jsonl')),
            list(lines(directory / 'missiles.jsonl')),
        )

    @property
    def recording(self) -> str | None:
        """The name of the recording this take is or was cut from, whatever its directory is called now:
        a trim carries it in its manifest, a recording is named by its start (RECORDING_NAME). None when
        neither says."""
        cut = self.manifest.get('trimmed') or {}
        root = cut.get('recording') or cut.get('take')
        if root:
            return root
        return self.directory.name if RECORDING_NAME.fullmatch(self.directory.name) else None

    @property
    def seconds(self) -> float:
        return self.frames[-1]['t'] - self.frames[0]['t'] if len(self.frames) > 1 else 0.0

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for event in self.events:
            counts[event['event']] = counts.get(event['event'], 0) + 1
        casts = [e for e in self.events if e['event'] == 'cast']
        return {
            'take': self.directory.name,
            'character': self.manifest.get('character'),
            'area': self.manifest.get('area'),
            'frames': len(self.frames),
            'late_frames': sum(f.get('late', 0) for f in self.frames),
            'seconds': round(self.seconds, 1),
            'rate_seen': round(len(self.frames) / self.seconds, 1) if self.seconds else None,
            'events': counts,
            'manual_casts': sum(not e.get('macro') for e in casts),
            'macro_casts': sum(bool(e.get('macro')) for e in casts),
            'monsters': len(self.units),
            'missiles': len(self.missiles),
            'missile_txt_ids': sorted({m['txt_id'] for m in self.missiles}),
        }


def timeline(take: Take, *, every: float = 5.0) -> list[str]:
    """One line per `every` seconds: the character, the monsters within a screen, casts and hits since."""
    if not take.frames:
        return []
    start = take.frames[0]['t']
    out, mark, casts, hits, kills = [], start, 0, 0, 0
    events = iter(take.events)
    pending = next(events, None)
    for frame in take.frames:
        while pending is not None and pending['t'] <= frame['t']:
            casts += pending['event'] == 'cast'
            hits += pending['event'] == 'hit'
            kills += pending['event'] == 'kill'
            pending = next(events, None)
        if frame['t'] - mark >= every or frame is take.frames[-1]:
            player = player_of(frame)
            near = 0
            if player is not None:
                near = sum(1 for m in monsters_of(frame) if m.alive and abs(m.x - player.x) + abs(m.y - player.y) <= 60)
            where = f'({player.x:.0f}, {player.y:.0f}) mode {player.mode}' if player is not None else 'no player'
            out.append(
                f'{frame["t"] - start:6.1f}s  {where:>28}  {near:2d} near  {len(frame["x"]):2d} missiles  '
                f'casts {casts:3d}  hits {hits:3d}  kills {kills:3d}  {"macro" if frame.get("macro") else ""}'
            )
            mark = frame['t']
    return out


def trim(take: Take, first: int, last: int, target: Path) -> Path:
    """Frames `first` to `last` of a take as a small take under `target`: the frames, the events in
    their time, the units and missiles seen in them, the manifest and the level map, gzipped. A cut
    of real play small enough to check in as a test fixture."""
    frames = [f for f in take.frames if first <= f['n'] <= last]
    if not frames:
        raise ValueError('no frames in the window')
    start, end = frames[0]['t'], frames[-1]['t']
    monsters = {m.unit for f in frames for m in monsters_of(f)}
    blades = {x.unit for f in frames for x in missiles_of(f)}
    target.mkdir(parents=True, exist_ok=True)
    parts = {
        'frames': frames,
        'events': [e for e in take.events if start <= e['t'] <= end],
        'units': [u for u in take.units if u['unit'] in monsters],
        'missiles': [
            {k: v for k, v in m.items() if k in ('t', 'unit_id', 'txt_id')}
            for m in take.missiles
            if m['unit_id'] in blades
        ],
    }
    for name, records in parts.items():
        with gzip.open(target / f'{name}.jsonl.gz', 'wt', encoding='utf-8') as handle:
            handle.writelines(json.dumps(record, separators=(',', ':')) + '\n' for record in records)
    manifest = {k: v for k, v in take.manifest.items() if k != 'census'}
    manifest['trimmed'] = {'take': take.directory.name, 'frames': [first, last]}
    if take.recording is not None:
        manifest['trimmed']['recording'] = take.recording  # kept through a trim of a trim
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True))
    level, packed = take.directory / 'level.json', take.directory / 'level.json.gz'
    if level.exists():
        with gzip.open(target / 'level.json.gz', 'wt', encoding='utf-8') as handle:
            handle.write(level.read_text())
    elif packed.exists():
        (target / 'level.json.gz').write_bytes(packed.read_bytes())
    return target
