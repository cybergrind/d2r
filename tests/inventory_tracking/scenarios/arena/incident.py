"""An incident: one recorded fight played again in the arena with the presses that were made, and the two
set side by side (architecture.md §6.2.3).

The trials (trials.py) ask how a rule changes many fights; an incident asks the question before that one:
does the arena, given the same start and the same presses, come to what the game came to? The scene is
cut at the incident's start, the macro is started as the session log says it was, and what the play comes
to is read at marks (seconds after the start) beside the recording:

- `taken`: the life lost by then (the take's `hurt` events; the arena's own count);
- `alive`: how many of the scene's hostiles still live;
- `strikes`: the strikes begun (in the take: the births of the strike's missiles, a cast's blades being
  born together; its `cast` events miss the casts made one after another on a held button);
- `low`: the least life seen, and `moved`: how far the character went, over the whole window.

A play is one roll of the monsters' dice, so the arena's side is a band over seeds: the recording is
`inside` when it lies between the 10th and the 90th percentile, else the row says by how much the median
is off. A row outside its band names something the arena does not hold yet; INCIDENTS.md lists what was
found for each.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.incident --seeds 30 --write
"""

import argparse
import json
import math
import statistics
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from itertools import pairwise
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.mechanics import MISSILE
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.macros.runner import ATTACK, PICKUP
from inventory_tracking.takes.takes import Take, missiles_of, monsters_of, player_of
from tests.inventory_tracking.scenarios.arena import scene as scene_file
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, cut
from tests.inventory_tracking.scenarios.arena.driver import Play, Press
from tests.inventory_tracking.scenarios.arena.game import Arena
from tests.inventory_tracking.scenarios.arena.scene import Prop, Scene


TAKES = Path('inventory_tracking/runs/combat')
FIXTURES = Path(__file__).parent / 'fixtures' / 'incidents'
CAST_GAP = 0.15  # seconds: missiles born further apart than this are of two casts
LOW, HIGH = 0.1, 0.9  # the band of the arena's plays the recording is looked for in


@dataclass(frozen=True)
class Incident:
    """A recorded fight to play again. `presses` are (seconds after `start`, the runner's routine), as the
    session log has the requests; `start` is seconds into the take."""

    name: str
    take: str
    start: float
    seconds: float
    presses: tuple[tuple[float, str], ...]
    marks: tuple[float, ...]
    about: str
    # What the session log says of the character and the take does not hold (`Hero` fields by name): the cut
    # scene has them from the defaults otherwise.
    hero: tuple[tuple[str, object], ...] = ()
    things: tuple[Prop, ...] = ()  # the objects the session log names (no take holds them)
    # What was done to the character that the arena's monsters do not do yet, as the take's `hurt` events
    # read it: (seconds after `start`, kind of damage, the share let through from then on, either weapon set).
    curses: tuple[tuple[float, str, float], ...] = ()


@dataclass(frozen=True)
class Track:
    """What a fight came to: `taken`, `alive` and `strikes` at each mark, `low` and `moved` over the window."""

    taken: tuple[float, ...]
    alive: tuple[int, ...]
    strikes: tuple[int, ...]
    low: float
    moved: float


INCIDENTS = (
    Incident(
        name='infector-seal',
        take='20261012T182157Z-108',
        start=161.96,
        seconds=10.0,
        # probe.log of session 20261012T181653Z-82a6bdb9, 21:24:39.45 on: the route turns attack mode on
        # at 40.41, the player's pickup key follows fourteen times.
        presses=(
            (0.96, ATTACK),
            *((at, PICKUP) for at in (1.25, 1.65, 3.07, 3.39, 3.99, 4.64, 5.54, 6.36, 6.86, 7.33, 7.94, 8.57, 9.25)),
        ),
        marks=(2.0, 4.0, 6.0, 8.0, 10.0),
        # 21:24:41.738 "InnerHellObject1 (object 798365376, class 125) at (7915.0, 5289.0) was not opened"
        things=(Prop(798365376, 125, (7915.0, 5289.0)),),
        hero=(('ward', False),),
        # The physical resistance read 10 at 0.2 s and -40 from 0.6 s to the window's end (evidence/CURSES.md:
        # an Oblivion Knight's curse; no half of the takes can fit it yet).
        curses=((0.6, 'physical', 1.4),),  # 21:24:40.418 "Psychic Ward": the mode's first cast, so the ward was down
        about=(
            'Chaos Sanctuary: the teleport step lands by the second Infector seal with the staff in hand, 13 '
            'monsters there already and the seal pack of 12 arriving; the character stands among them for the '
            'whole fight.'
        ),
    ),
)


def hostile_units(scene: Scene) -> frozenset[int]:
    return frozenset(mob.unit for mob in scene.mobs if mob.owner is None and not mob.ally and mob.life > 0)


def births(frames: Sequence[dict], missile: int) -> list[float]:
    """The times at which casts of `missile` began: its units' first frames, those within CAST_GAP as one."""
    seen = {row.unit for row in missiles_of(frames[0]) if row.txt == missile} if frames else set()
    found: list[float] = []
    for frame in frames[1:]:
        fresh = {row.unit for row in missiles_of(frame) if row.txt == missile} - seen
        seen |= fresh
        if fresh and (not found or frame['t'] - found[-1] > CAST_GAP):
            found.append(frame['t'])
    return found


def recorded(take: Take, incident: Incident, scene: Scene, missile: int = MISSILE) -> Track:
    """The recording's track over the incident's window."""
    zero = take.frames[0]['t']
    start, end = zero + incident.start, zero + incident.start + incident.seconds
    units = hostile_units(scene)
    frames = [frame for frame in take.frames if start <= frame['t'] <= end]
    casts = births(frames, missile)
    taken, alive, strikes = [], [], []
    for mark in incident.marks:
        until = start + mark
        events = [event for event in take.events if start < event['t'] <= until]
        taken.append(float(sum(event.get('lost', 0) for event in events if event.get('event') == 'hurt')))
        strikes.append(sum(1 for at in casts if at <= until))
        living = set(units)
        for frame in frames:
            if frame['t'] > until:
                break
            for monster in monsters_of(frame):
                if monster.unit in units and not monster.alive:
                    living.discard(monster.unit)
        alive.append(len(living))
    rows = [row for frame in frames if (row := player_of(frame)) is not None]
    lives = [row.life for row in rows if row.life and row.max_life]
    moved = sum(math.dist(a.at, b.at) for a, b in pairwise(rows))
    return Track(tuple(taken), tuple(alive), tuple(strikes), float(min(lives, default=0)), round(moved, 1))


def played(scene: Scene, incident: Incident, seed: int) -> Track:
    """One play of the incident in the arena, the standalone healer beside the macro as in the game."""
    arena = Arena(scene, seed=seed, osd=PLAYER_HEALING)
    presses = [Press(at, routine) for at, routine in incident.presses]
    play = Play(arena, presses, incident.seconds, seed)
    samples: list[tuple[float, float, int, int]] = []
    low = [arena.life]
    spy = play.tick

    due = sorted(incident.curses)

    def tick() -> None:
        while due and due[0][0] <= arena.clock.now + 1e-9:
            _, kind, share = due.pop(0)
            for resist in arena.resists:
                resist[kind] = share
        samples.append((arena.clock.now, arena.taken, len(arena.mobs.live()), arena.casts))
        low[0] = min(low[0], arena.life)
        spy()

    play.tick = tick  # type: ignore[method-assign]
    result = play.run()
    taken, alive, strikes = [], [], []
    for mark in incident.marks:
        past = [sample for sample in samples if sample[0] <= mark + 1e-9] or samples[:1]
        last = past[-1] if past else (0.0, 0.0, len(hostile_units(scene)), 0)
        taken.append(round(last[1], 1))
        alive.append(last[2])
        strikes.append(last[3])
    return Track(tuple(taken), tuple(alive), tuple(strikes), round(max(low[0], 0.0), 1), round(result.moved, 1))


@dataclass(frozen=True)
class Row:
    """One quantity at one mark: the recording against the arena's band."""

    what: str
    recorded: float
    low: float
    median: float
    high: float

    @property
    def inside(self) -> bool:
        return self.low <= self.recorded <= self.high

    @property
    def verdict(self) -> str:
        if self.inside:
            return 'inside'
        if not self.recorded or not self.median:
            return 'outside'
        return f'outside: the arena has {self.median / self.recorded:.2f} of it'


def quantile(values: Sequence[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))]


def compare(truth: Track, plays: Sequence[Track], marks: Sequence[float]) -> list[Row]:
    rows: list[Row] = []

    def row(what: str, real: float, values: Sequence[float]) -> None:
        rows.append(Row(what, real, quantile(values, LOW), statistics.median(values), quantile(values, HIGH)))

    for index, mark in enumerate(marks):
        row(f'taken by {mark:g} s', truth.taken[index], [play.taken[index] for play in plays])
    for index, mark in enumerate(marks):
        row(f'alive at {mark:g} s', truth.alive[index], [play.alive[index] for play in plays])
    for index, mark in enumerate(marks):
        row(f'strikes by {mark:g} s', truth.strikes[index], [play.strikes[index] for play in plays])
    row('least life', truth.low, [play.low for play in plays])
    row('moved', truth.moved, [play.moved for play in plays])
    return rows


def table(incident: Incident, rows: Sequence[Row], seeds: int) -> str:
    inside = sum(1 for row in rows if row.inside)
    lines = [
        f'## {incident.name}',
        '',
        incident.about,
        '',
        f'Take {incident.take}, {incident.start:g} s in, {incident.seconds:g} s; {seeds} seeds. '
        f'**{inside} of {len(rows)} rows inside the band.**',
        '',
        '| | recorded | arena p10 | median | p90 | |',
        '| --- | ---: | ---: | ---: | ---: | --- |',
    ]
    lines += [
        f'| {row.what} | {row.recorded:g} | {row.low:g} | {row.median:g} | {row.high:g} | {row.verdict} |'
        for row in rows
    ]
    return '\n'.join(lines) + '\n'


def stored(incident: Incident) -> tuple[Scene, Track] | None:
    """The incident's scene and recorded track as kept in the fixtures; None: not cut yet."""
    scene_path, track_path = FIXTURES / f'{incident.name}.json', FIXTURES / f'{incident.name}.recorded.json'
    if not scene_path.exists() or not track_path.exists():
        return None
    track = json.loads(track_path.read_text(encoding='utf-8'))
    return scene_file.load(scene_path), Track(**{key: _tuple(value) for key, value in track.items()})  # type: ignore[arg-type]


def _tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


def store(incident: Incident, takes: Path = TAKES) -> tuple[Scene, Track]:
    """Cut the incident from its take and keep the scene and the recorded track in the fixtures."""
    take = Take.load(takes / incident.take)
    zero = take.frames[0]['t']
    frame = next(index for index, row in enumerate(take.frames) if row['t'] - zero >= incident.start)
    scene = cut(take, frame, defaults=DEFAULT_HERO, name=incident.name)
    known = dict(incident.hero)
    scene.hero = replace(scene.hero, **known)  # type: ignore[arg-type]
    scene.assumed = tuple(name for name in scene.assumed if name not in known)
    scene.things = [replace(prop) for prop in incident.things]
    truth = recorded(take, incident, scene)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    scene_file.dump(scene, FIXTURES / f'{incident.name}.json')
    text = json.dumps(asdict(truth), indent=1)
    (FIXTURES / f'{incident.name}.recorded.json').write_text(text + '\n', encoding='utf-8')
    return scene, truth


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('names', nargs='*', help='incidents to play (default: all)')
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--cut', action='store_true', help='cut the scenes again from the takes')
    parser.add_argument('--write', action='store_true', help='write fixtures/incidents/INCIDENTS.md')
    args = parser.parse_args(argv)
    parts = []
    for incident in INCIDENTS:
        if args.names and incident.name not in args.names:
            continue
        found = store(incident) if args.cut else stored(incident) or store(incident)
        scene, truth = found
        plays = [played(scene, incident, seed) for seed in range(1, args.seeds + 1)]
        parts.append(table(incident, compare(truth, plays, incident.marks), args.seeds))
    text = '# Incidents: the recording against the arena\n\n' + '\n'.join(parts)
    print(text)
    if args.write:
        (FIXTURES / 'INCIDENTS.md').write_text(text, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
