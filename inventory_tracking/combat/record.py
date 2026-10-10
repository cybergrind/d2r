"""Stage 1 of combat/plan.md: takes of real play, sampled at the game's frame rate.

A take is one stay in a recorded level (Chaos Sanctuary first, user 2026-10-09) under
`runs/combat/<timestamp>-<area>/`: `manifest.json` (character, skills, slots, rate, key names,
the level map in `level.json` when the guide has one), `frames.jsonl` (one line per frame: the
player, every monster with its life, dead ones included, every missile raw, the pointer with its
button mask and the keys down, the macro state), `units.jsonl` (each monster's full stat list on
first sight: level, defence, resistances for stage 3), `missiles.jsonl` (each missile's whole
record on first sight: the layout research of stage 1) and `events.jsonl` (casts, hits, kills,
unloads, button and key changes, derived while recording). Reads only; nothing touches the game.

`Recorder.step` is the per-frame logic with the clock injected; `Recorder.run` paces it on its
own thread with its own memory handle and display connection (`LiveSampler`), bound to the game
by `poll` from the service loop as the macro runner is.
"""

import dataclasses
import json
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG, timestamp
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.levels.model import Level
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.world import NO_OWNER, GameMemory, World
from inventory_tracking.native.layout import DEAD_MODES


SCHEMA = 2  # the rows' layout (takes.py `SCHEMAS`): written to the manifest since 2026-10-10 night
FRAME_RATE = 25.0  # the engine's frames per second
AREAS = frozenset((108,))  # Chaos Sanctuary
IDLE_SECONDS = 3.0  # out of the areas or out of a game this long: the take closes
LEVEL_SECONDS = 5.0  # between looks at the guide's walls while a take runs (level.json grows with them)
CENSUS_SECONDS = 30.0  # between unit table censuses (research: where the missiles hang)
BUTTON_BITS = {1: 1 << 8, 2: 1 << 9, 3: 1 << 10, 8: 1 << 15, 9: 1 << 16}  # XQueryPointer mask bits
# life, max life, mana, max mana: itemstatcost ids 6 hitpoints, 7 maxhp, 8 mana, 9 maxmana (values carry 8 fraction
# bits). Takes before 2026-10-10 10:00 UTC read 9 and 11 (maxmana, maxstamina): their mana columns are those maxima.
VITAL_STATS = (6, 7, 8, 9)
# Keys whose codes the manifest names, so the frames' key codes can be read: the skill keys, the
# teleport key, the modifiers and Show Items.
NAMED_KEYS = (
    'a',
    's',
    'd',
    'f',
    'g',
    'x',
    'q',
    'w',
    'e',
    'r',
    't',
    '6',
    '7',
    'z',
    'c',
    'KP_5',
    'Shift_L',
    'Control_L',
    'Alt_L',
)


@dataclass(frozen=True)
class Sample:
    """What one frame reads."""

    world: World
    missiles: list[dict] = dataclasses.field(default_factory=list)
    pointer: tuple[int, int, int] | None = None  # x, y, button mask (root coordinates)
    rect: tuple[int, int, int, int] | None = None  # the game window
    keys: frozenset[int] = frozenset()  # key codes down
    macro: bool = False  # a macro run was acting
    census: list[dict] | None = None  # the unit table census, when the sampler took one this frame


class Take:
    """One take's files; `frame` writes a frame and the events it implies."""

    def __init__(self, directory: Path, manifest: dict[str, Any], stats: Callable[[int], dict[int, int]]) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest
        self.stats = stats
        self.frames = (directory / 'frames.jsonl').open('w', encoding='utf-8')
        self.events = (directory / 'events.jsonl').open('w', encoding='utf-8')
        self.units = (directory / 'units.jsonl').open('w', encoding='utf-8')
        self.missiles = (directory / 'missiles.jsonl').open('w', encoding='utf-8')
        self.count, self.late = 0, 0
        self.started: float | None = None
        self.last_clock: float | None = None
        self.counts: dict[str, int] = {}
        self.seen_units: set[int] = set()
        self.seen_missiles: set[int] = set()
        self.life: dict[int, tuple[int, int]] = {}  # unit id -> (txt id, life) at the last frame
        self.dead: set[int] = set()
        self.acting = False
        self.mask = 0
        self.keys: frozenset[int] = frozenset()
        self.write_manifest()

    def write_manifest(self) -> None:
        (self.directory / 'manifest.json').write_text(json.dumps(self.manifest, indent=1, sort_keys=True))

    def vitals(self, player) -> list[int]:
        stats = self.stats(player.stats_at) if player.stats_at else {}
        return [stats.get(stat, 0) >> 8 for stat in VITAL_STATS]

    def event(self, clock: float, kind: str, **fields: Any) -> None:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        self.events.write(json.dumps({'t': round(clock, 3), 'event': kind, **fields}) + '\n')

    def frame(self, clock: float, sample: Sample, late: int = 0) -> None:
        world = sample.world
        player = world.player
        if self.started is None:
            self.started = clock
        self.count += 1
        self.late += late
        self.last_clock = clock
        fx = fy = None
        if sample.pointer is not None and sample.rect is not None and sample.rect[2] and sample.rect[3]:
            fx = round((sample.pointer[0] - sample.rect[0]) / sample.rect[2], 4)
            fy = round((sample.pointer[1] - sample.rect[1]) / sample.rect[3], 4)
        monsters = [
            [
                m.unit_id,
                m.txt_id,
                m.mode,
                round(m.x, 2),
                round(m.y, 2),
                m.life,
                m.max_life,
                m.flags,
                m.owner,
                int(m.ally),
            ]
            for m in world.monsters
        ]
        character = None
        if player is not None:
            at = (round(player.x, 2), round(player.y, 2))
            character = [player.unit_id, player.mode, player.area, *at, player.left_skill, player.right_skill]
            character += self.vitals(player)  # life, max life, mana, max mana (whole points), since 2026-10-10
        line = {
            't': round(clock, 3),
            'n': self.count,
            'late': late,
            'game': world.in_game,
            'panels': list(world.open_panels),
            'macro': sample.macro,
            'p': character,
            'm': monsters,
            'x': [[x['unit_id'], x['txt_id'], x['mode'], *x['xy'], x['path']] for x in sample.missiles],
            'd': [[d.unit_id, d.txt_id, d.mode, d.x, d.y] for d in world.doors],
            'in': [*(sample.pointer or (None, None, None)), fx, fy, sorted(sample.keys)],
            'rect': list(sample.rect) if sample.rect else None,
        }
        self.frames.write(json.dumps(line, separators=(',', ':')) + '\n')
        if sample.census is not None:
            self.manifest.setdefault('census', []).append({'t': round(clock, 3), 'slots': sample.census})
            LOG.info('Combat take %s: unit table census %s', self.directory.name, sample.census)
        self.derive(clock, sample)

    def derive(self, clock: float, sample: Sample) -> None:
        world = sample.world
        player = world.player
        if player is not None:
            acting = player.mode in ACTING
            if acting != self.acting:
                self.event(clock, 'cast' if acting else 'cast_end', mode=player.mode, macro=sample.macro)
            self.acting = acting
        present = set()
        for m in world.monsters:
            present.add(m.unit_id)
            if m.ally or m.owner != NO_OWNER:
                self.life[m.unit_id] = (m.txt_id, m.life)  # the pets and the mercenary: no hit or kill events
                continue
            if m.unit_id not in self.seen_units:
                self.seen_units.add(m.unit_id)
                unit: dict[str, Any] = {'t': round(clock, 3), 'unit': m.unit_id, 'txt': m.txt_id, 'flags': m.flags}
                unit.update(owner=m.owner, ally=m.ally, max_life=m.max_life, stats=self.stats(m.stats_at))
                self.units.write(json.dumps(unit) + '\n')
            before = self.life.get(m.unit_id)
            if before is not None and m.max_life and m.life < before[1]:
                self.event(clock, 'hit', unit=m.unit_id, txt=m.txt_id, life=[before[1], m.life], macro=sample.macro)
            if m.mode in DEAD_MODES and m.unit_id not in self.dead:
                self.dead.add(m.unit_id)
                self.event(clock, 'kill', unit=m.unit_id, txt=m.txt_id, macro=sample.macro)
            self.life[m.unit_id] = (m.txt_id, m.life)
        for unit_id in list(self.life):
            if unit_id not in present:
                txt, life = self.life.pop(unit_id)
                if unit_id not in self.dead:
                    self.event(clock, 'gone', unit=unit_id, txt=txt, life=life)
        for x in sample.missiles:
            if x['unit_id'] not in self.seen_missiles:
                self.seen_missiles.add(x['unit_id'])
                self.missiles.write(json.dumps({'t': round(clock, 3), **x}) + '\n')
        mask = sample.pointer[2] if sample.pointer is not None else 0
        for button, bit in BUTTON_BITS.items():
            if (mask & bit) != (self.mask & bit):
                self.event(clock, 'button', button=button, down=bool(mask & bit))
        self.mask = mask
        if sample.keys != self.keys:
            self.event(clock, 'keys', down=sorted(sample.keys - self.keys), up=sorted(self.keys - sample.keys))
        self.keys = sample.keys

    def close(self, reason: str) -> None:
        for handle in (self.frames, self.events, self.units, self.missiles):
            handle.close()
        duration = (self.last_clock - self.started) if self.started is not None and self.last_clock is not None else 0.0
        summary = {'frames': self.count, 'late_frames': self.late, 'seconds': round(duration, 3), 'events': self.counts}
        summary.update(monsters=len(self.seen_units), missiles=len(self.seen_missiles))
        self.manifest.update(finished_at=timestamp(), reason=reason, **summary)
        self.write_manifest()
        LOG.info('Combat take %s closed (%s): %s', self.directory.name, reason, summary)


class Recorder:
    """Per-frame logic: opens a take when the character is in a recorded level, closes it after
    IDLE_SECONDS elsewhere or when the character enters another recorded level (one take per stay in a
    level, since 2026-10-10: the first Catacombs take spanned three levels and so never matched the
    guide's level map). `sample()` reads one frame or gives None when the game cannot be read."""

    def __init__(
        self,
        sample: Callable[[], Sample | None],
        *,
        output: Path,
        areas: frozenset[int] = AREAS,
        rate: float = FRAME_RATE,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        level: Callable[[], Level | None] | None = None,
        stats: Callable[[int], dict[int, int]] = lambda stats_at: {},
        manifest: Callable[[], dict[str, Any]] = dict,
    ) -> None:
        self.sample, self.output, self.areas, self.rate = sample, output, areas, rate
        self.clock, self.sleep, self.level, self.stats, self.manifest = clock, sleep, level, stats, manifest
        self.take: Take | None = None
        self.away_since: float | None = None  # when the character was last seen outside the areas
        self.takes = 0
        self.level_at = -math.inf  # when the guide's level was last looked at for the take

    def step(self, now: float, late: int = 0) -> None:
        """One frame: `late` is how many frame periods this one came after its time."""
        sample = self.sample()
        world = sample.world if sample is not None else None
        player = world.player if world is not None else None
        if (
            sample is not None
            and world is not None
            and world.in_game
            and player is not None
            and player.area in self.areas
        ):
            self.away_since = None
            if self.take is not None and player.area != self.take.manifest.get('area'):
                self.close('changed level')
            if self.take is None:
                self.open(now, sample, player.area)
            elif now - self.level_at >= LEVEL_SECONDS:
                self.write_level(self.take, now)  # the walls the guide read since
        elif self.take is not None:
            self.away_since = now if self.away_since is None else self.away_since
            if now - self.away_since >= IDLE_SECONDS or (world is not None and not world.in_game):
                self.close('left the level' if world is None or world.in_game else 'left the game')
                return
        if self.take is not None and sample is not None:
            self.take.frame(now, sample, late)

    def open(self, now: float, sample: Sample, area: int) -> None:
        self.takes += 1
        player = sample.world.player
        name = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + f'-{area}'
        manifest = {
            'started_at': timestamp(), 'area': area, 'rate': self.rate, 'schema': SCHEMA,
            'character': player.name if player else None,
            'slots': list(sample.world.slots), 'left_skill': player.left_skill if player else None,
            'right_skill': player.right_skill if player else None, **self.manifest(),
        }  # fmt: skip
        self.take = Take(self.output / name, manifest, self.stats)
        self.write_level(self.take, now)
        LOG.info('Combat take %s opened in area %d', name, area)

    def close(self, reason: str) -> None:
        if self.take is not None:
            self.write_level(self.take, self.clock())  # the walls read while the take ran
            self.take.close(reason)
            self.take = None
        self.away_since = None

    def write_level(self, take: Take, now: float) -> None:
        """Copy the guide's level beside the take when it is this level's and says more than the copy
        (more grids read); the guide forgets the walls on leaving the game, so never less."""
        self.level_at = now
        level = self.level() if self.level is not None else None
        if level is None or level.area != take.manifest.get('area'):
            return
        if len(level.ground) > take.manifest.get('level_grids', -1):
            (take.directory / 'level.json').write_text(json.dumps(dataclasses.asdict(level)))
            take.manifest['level'], take.manifest['level_grids'] = 'level.json', len(level.ground)

    def run(self, stop: threading.Event) -> None:
        """Pace `step` at `rate` until `stop`; a frame that comes late is counted, not caught up."""
        period = 1 / self.rate
        next_frame = self.clock()
        while not stop.is_set():
            now = self.clock()
            late = int((now - next_frame) * self.rate + 1e-6) if now > next_frame else 0
            try:
                self.step(now, late)
            except Exception:
                LOG.exception('Combat recorder: a frame failed')
            next_frame = max(next_frame, now) + period  # a late frame resets the schedule: no catching up
            wait = next_frame - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.close('stopped')


class LiveSampler:
    """`Recorder.sample` for the running game: its own memory handle, bound by `attach` from the
    service loop, and its own display connection opened on the recorder's thread."""

    def __init__(
        self, macro_working: Callable[[], bool] = lambda: False, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.memory: GameMemory | None = None
        self.bound: tuple[int, int, int] | None = None
        self.keys = None
        self.macro_working = macro_working
        self.clock = clock
        self.lock = threading.Lock()
        self.key_names: dict[int, str] = {}
        self.census_at = -math.inf

    def attach(self, pid: int, base: int, table: int) -> None:
        if self.bound == (pid, base, table):
            return
        with self.lock:
            if self.memory is not None:
                self.memory.close()
            self.memory = GameMemory(pid, base, table)
            self.bound = (pid, base, table)

    def detach(self) -> None:
        with self.lock:
            if self.memory is not None:
                self.memory.close()
            self.memory, self.bound = None, None

    def name_keys(self) -> dict[int, str]:
        """Key code -> name for NAMED_KEYS, read once from the display."""
        if self.keys is not None and not self.key_names:
            codes = self.keys.keycodes([name.encode() for name in NAMED_KEYS]) or []
            self.key_names = dict(zip(codes, NAMED_KEYS, strict=False))
        return self.key_names

    def stats(self, stats_at: int) -> dict[int, int]:
        with self.lock:
            return self.memory.stats(stats_at) if self.memory is not None and stats_at else {}

    def __call__(self) -> Sample | None:
        with self.lock:
            memory = self.memory
            if memory is None:
                return None
            census = None
            try:
                world = memory.world()
                if world.in_game and world.player is not None:
                    world = dataclasses.replace(world, monsters=memory.all_monsters())
                missiles = memory.missiles() if world.in_game else []
                if world.in_game and self.clock() - self.census_at >= CENSUS_SECONDS:
                    self.census_at = self.clock()
                    census = memory.census()
            except (OSError, ValueError) as exc:
                LOG.debug('Combat recorder: read failed (%s)', exc)
                return None
        pointer = rect = None
        keys: frozenset[int] = frozenset()
        if self.keys is not None:
            pointer, rect, keys = self.keys.pointer_state(), self.keys.focused_window_rect(), self.keys.held_keys()
        return Sample(world, missiles, pointer, rect, keys, self.macro_working(), census)


class CombatRecorder:
    """The service's handle: `poll` binds the game, the thread records."""

    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        output: Path,
        areas: frozenset[int] = AREAS,
        rate: float = FRAME_RATE,
        level: Callable[[], Level | None] | None = None,
        macro_working: Callable[[], bool] = lambda: False,
        poll_interval: float = 1.0,
    ) -> None:
        self.source, self.capture_lock = source, capture_lock
        self.sampler = LiveSampler(macro_working)
        self.recorder = Recorder(
            self.sampler, output=output, areas=areas, rate=rate, level=level, stats=self.sampler.stats,
            manifest=lambda: {'keys': {str(code): name for code, name in self.sampler.name_keys().items()}},
        )  # fmt: skip
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name='combat-recorder', daemon=True)
        self.last_poll = -math.inf
        self.poll_interval = poll_interval
        self.warned = False
        self.thread.start()

    def _run(self) -> None:
        with X11Keyboard().connect(exclusive=False) as keys:
            self.sampler.keys = keys
            self.recorder.run(self.stop)

    def poll(self, now: float) -> None:
        if now - self.last_poll < self.poll_interval or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            self.source.ensure_connected()
            tables = {found['table_address'] for found in self.source.capture['unit_table_candidates']}
            if len(tables) != 1:
                raise ValueError('the game is not attached')
            self.sampler.attach(self.source.pid, self.source.images['candidate_base'], next(iter(tables)))
            self.warned = False
        except Exception as exc:
            self.sampler.detach()
            if not self.warned:
                LOG.info('Combat recorder: waiting for the game (%s)', exc)
                self.warned = True
        finally:
            self.capture_lock.release()

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=3)
        self.sampler.detach()
