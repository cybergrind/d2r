"""Stage 1 of combat/plan.md: takes of real play, sampled at the game's frame rate. Reads only.

A take is one stay in a recorded level under `runs/combat/<timestamp>-<area>/`: `manifest.json` (character, skills,
keys, clock, game, code), `frames.jsonl` (per frame: the player, monsters, missiles, pointer, keys, and keys that are
written only when they change: `r` resists, `o` objects, `s` states, `w` staff, `b` belt, `f` buffs, `g` ground,
`i` inventory, `a` ward, `h` hovered, `k` tick, `sf` server frame), `units.jsonl`, `missiles.jsonl`, `records.jsonl`
(raw unit records) and `events.jsonl` (casts, hits, kills, `hurt`, the macro's `request`/`press`/`said`/`log`/
`state`, `sent` inputs, `load`, `input_mode`, `ctl`). The take format, key by key: takes/README.md.

`Recorder.step` is the per-frame logic with the clock injected; `Recorder.run` paces it on its own thread with its
own memory handle and display connection (`LiveSampler`), bound to the game by `poll` as the macro runner is.
"""

import collections
import dataclasses
import json
import logging
import math
import struct
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from inventory_tracking.common import LOG, timestamp
from inventory_tracking.game.layout import ACTING, ITEM_UNIT, NO_OWNER
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Loot, Monster, Player, Teleport, Thing, World
from inventory_tracking.input import gamepad, sent
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.items.identity import QUALITY_OFFSET
from inventory_tracking.items.metadata import item_base
from inventory_tracking.levels.model import Level
from inventory_tracking.native.layout import DEAD_MODES, TOWN_IDS
from inventory_tracking.native.memory import one_unit_table
from inventory_tracking.native.units import walk_units
from inventory_tracking.takes import hurts, retain


SCHEMA = 4  # the rows' layout (takes.py `SCHEMAS`): written to the manifest since 2026-10-10 night
FRAME_RATE = 25.0  # the engine's frames per second
AREAS = frozenset((108,))  # Chaos Sanctuary
IDLE_SECONDS = 3.0  # out of the areas or out of a game this long: the take closes
LEVEL_SECONDS = 5.0  # between looks at the guide's walls while a take runs (level.json grows with them)
RECORD_SECONDS = 1.0  # a unit's raw record is written at a change of mode and at least this often
NOTE_SECONDS = 120.0  # the macro's word from before a take is kept this long for the take's start
NOTE_MOST = 2000
# The service's own inputs kept outside a take (NOTE_SECONDS) at most: a move is 4 to 18 pointer steps.
SENT_MOST = 8000
SLOW_SECONDS = 0.2  # between reads of what changes slowly and costs a walk of a unit table (`o`, `w`, `b`)
CENSUS_SECONDS = 30.0  # between unit table censuses (research: where the missiles hang)
BUTTON_BITS = {1: 1 << 8, 2: 1 << 9, 3: 1 << 10, 8: 1 << 15, 9: 1 << 16}  # XQueryPointer mask bits
# life, max life, mana, max mana: itemstatcost ids 6-9 (8 fraction bits). Takes before 2026-10-10 10:00 UTC read 9
# and 11 (maxmana, maxstamina) as mana.
VITAL_STATS = (6, 7, 8, 9)
# The character's resistances as its stat list holds them: itemstatcost 36 damageresist (physical), 39 fire,
# 41 lightning, 43 cold, 45 poison. A curse shows in them.
RESIST_STATS = (36, 39, 41, 43, 45)
# The Psychic Ward's pool (skills.txt 387, state 206): itemstatcost 361 `psychicward` (left) and 362
# `psychicwardmax` (as cast), x256 as life is; in the stat list only while the ward is up.
WARD_STATS = (361, 362)
# The server's frame (+0x28) of the last life message the client took (0x18, 0x95): the u32 at
# [[unit +0x10] +0x218] +0xC4 of the character (rca/2026-10-13/re-findings.md, "How to read it live").
PLAYER_DATA, LIFE_BLOCK, LIFE_FRAME = 0x10, 0x218, 0xC4
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
    '1',
    '2',
    '3',
    '4',
)
# A pad event's (type, code) -> the name a `sent` event gives it (input/gamepad.py).
PAD_INPUTS = {
    **{(gamepad.EV_KEY, code): name for name, code in gamepad.BUTTONS.items()},
    **{(gamepad.EV_ABS, axis): name for name, axis in gamepad.TRIGGERS.items()},
    (gamepad.EV_ABS, gamepad.ABS_X): 'left x',
    (gamepad.EV_ABS, gamepad.ABS_Y): 'left y',
    (gamepad.EV_ABS, gamepad.ABS_RX): 'right x',
    (gamepad.EV_ABS, gamepad.ABS_RY): 'right y',
    (gamepad.EV_ABS, gamepad.ABS_HAT0X): 'dpad x',
    (gamepad.EV_ABS, gamepad.ABS_HAT0Y): 'dpad y',
}


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
    things: tuple[Thing, ...] | None = None  # the objects a mark may name and the containers; None: unread
    states: bytes | None = None  # the character's state words (game/layout.py STATE_RUN)
    staff: Teleport | None = None  # the worn Teleport staff; None: none worn, or unread
    belt: tuple[int | None, ...] | None = None  # item class by belt cell
    loot: Loot | None = None  # the drops the pickup step would go for and the inventory's room; None: unread
    macro_state: dict[str, Any] | None = None  # what the macro carries (takes/macro_state.py); None: not asked
    tick: bytes | None = None  # the head of the client's clock object (game/memory.py `tick`)
    hovered: tuple[int, int] | None = None  # (unit type, unit id) under the pointer
    hover_read: bool = False  # the read of it was made (None then means nothing is under the pointer)
    items: dict[int, tuple[str | None, int | None]] | None = None  # drop unit id -> (item code, quality)


class Before(NamedTuple):
    """The frame before, as a blow is judged against it: it lands between two."""

    unit: int  # the character's unit
    life: int
    max_life: int
    at: hurts.Point
    foes: list[hurts.Foe]
    flying: list[tuple[int, hurts.Point]]
    absorb: tuple[float, float]  # an absorb pool (the Warlock's Psychic Ward): left, most (WARD_STATS)
    companions: dict[int, tuple[int, int, int]]  # unit -> (txt, life, max life) of the mercenary and the pets


def points(raw: int) -> float:
    """A stat held x256 (life, the ward's pool) in points."""
    return round(raw / 256, 2)


def item_identity(read, table: int, unit_id: int) -> tuple[str | None, int | None]:
    """(code, quality) of the item unit `unit_id`: the code by its class (items/data/item_metadata.json `bases`),
    the quality from item data +0x00 (1 low to 8 crafted); one hash chain walked. (None, None) when unread."""
    try:
        bucket = unit_id % 128
        head = struct.unpack('<Q', read(table + ITEM_UNIT * 1024 + 8 * bucket, 8))[0]
        heads = [0] * 128
        heads[bucket] = head
        for unit in walk_units(read, heads, ITEM_UNIT)['units']:
            if unit['unit_id'] != unit_id:
                continue
            quality = None
            if unit['data_pointer']:
                quality = struct.unpack_from('<I', read(unit['data_pointer'] + QUALITY_OFFSET, 4))[0]
            base = item_base(unit['txt_id'])
            return (base['code'] if base else None, quality)
    except OSError, ValueError, struct.error:
        pass
    return (None, None)


def companion_of(monster: Monster, character: int) -> bool:
    """The mercenary or a pet of the character's, alive."""
    return (monster.ally or monster.owner == character) and monster.mode not in DEAD_MODES


class Take:
    """One take's files; `frame` writes a frame and the events it implies."""

    def __init__(
        self,
        directory: Path,
        manifest: dict[str, Any],
        stats: Callable[[int], dict[int, int]],
        server_frame: Callable[[Player], int | None] | None = None,
    ) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest
        self.stats = stats
        self.server_frame = server_frame  # read in a frame whose life differs from the frame before (`sf`)
        self.last_life: int | None = None  # the character's life in the frame before
        self.life_frame: int | None = None  # the server frame of the life message read last
        self.absorb: tuple[float, float] = (0.0, 0.0)  # the ward's pool at the last frame: left, most
        self.unit_states: dict[int, bytes] = {}  # unit id -> its state words at the last frame
        self.unit_stats: dict[int, dict[int, int]] = {}  # unit id -> its stat list as written last
        self.frames = (directory / 'frames.jsonl').open('w', encoding='utf-8')
        self.events = (directory / 'events.jsonl').open('w', encoding='utf-8')
        self.units = (directory / 'units.jsonl').open('w', encoding='utf-8')
        self.missiles = (directory / 'missiles.jsonl').open('w', encoding='utf-8')
        self.paths = (directory / 'paths.jsonl').open('w', encoding='utf-8')
        self.records = (directory / 'records.jsonl').open('w', encoding='utf-8')
        self.recorded: dict[int, tuple[int, float]] = {}  # unit id -> (mode, clock) of its record written last
        self.macro_state: dict[str, Any] | None = None  # the macro's state as the last `state` event has it
        self.path_rest: dict[int, bytes] = {}  # unit id -> its path record past the position, as last written
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
        self.mods: dict[int, tuple[int, ...]] = {}  # unit id -> its enchantments, as first seen
        self.resists: list[int] = []  # the character's RESIST_STATS at the last frame
        self.written_resists: list[int] | None = None  # the ones in the last frame that has `r`
        self.written: dict[str, Any] = {}  # frame key (`o`, `s`, `w`, `b`) -> its value as written last
        self.before: Before | None = None  # the frame before (a blow lands between two)
        self.decision: dict[str, Any] | None = None
        self.write_manifest()

    def write_manifest(self) -> None:
        (self.directory / 'manifest.json').write_text(json.dumps(self.manifest, indent=1, sort_keys=True))

    def vitals(self, player) -> list[int]:
        stats = self.stats(player.stats_at) if player.stats_at else {}
        self.resists = [stats.get(stat, 0) for stat in RESIST_STATS]
        left, most = (points(stats.get(stat, 0)) for stat in WARD_STATS)
        self.absorb = (left, most)
        return [stats.get(stat, 0) >> 8 for stat in VITAL_STATS]

    def read_life_frame(self, player: Player, life: int) -> None:
        """`life_frame` read in the first frame with the character and again when the life differs from the
        frame before: only a life message changes either (`sf`)."""
        changed = life != self.last_life
        self.last_life = life
        if changed and self.server_frame is not None:
            found = self.server_frame(player)
            if found is not None:
                self.life_frame = found

    def event(self, clock: float, kind: str, **fields: Any) -> None:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        self.events.write(json.dumps({'t': round(clock, 3), 'event': kind, **fields}) + '\n')

    def sent(
        self,
        at: float,
        kind: str,
        what: tuple[int, ...],
        by: str,
        routine: str | None,
        rect: tuple[int, int, int, int] | None,
    ) -> None:
        """A `sent` event: one input of the service's own (`Recorder.sent`), written with a frame whose game
        window `rect` turns a pointer target into fractions."""
        fields: dict[str, Any] = {'input': kind}
        if kind in ('key', 'button') and len(what) == 2:
            code, down = what
            if kind == 'key':
                fields.update(code=code, down=bool(down), name=self.manifest.get('keys', {}).get(str(code)))
            else:
                fields.update(button=code, down=bool(down))
        elif kind == 'move' and len(what) == 2:
            fields['xy'] = list(what)
            if rect is not None and rect[2] and rect[3]:
                fields['f'] = [round((what[0] - rect[0]) / rect[2], 4), round((what[1] - rect[1]) / rect[3], 4)]
        elif kind == 'pad' and len(what) == 3:
            fields.update(name=PAD_INPUTS.get(what[:2]), value=what[2], ev=list(what[:2]))
        else:
            fields['raw'] = list(what)
        fields['by'] = by
        if routine is not None:
            fields['routine'] = routine
        self.event(at, 'sent', **fields)

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
            vitals = self.vitals(player)
            character += vitals  # life, max life, mana, max mana (whole points), since 2026-10-10
            self.read_life_frame(player, vitals[0])
            self.hurt(clock, sample, player, vitals[0], vitals[1])
        else:
            self.before = None
            self.last_life = None
        line: dict[str, Any] = {
            't': round(clock, 3),
            'n': self.count,
            'late': late,
            'game': world.in_game,
            'panels': list(world.open_panels),
            # 0 while the game loads (world.VIEW_RVA): how long a waypoint's or a portal's level change loads
            # (rca/2026-10-16/loop-first-game-findings.md §2)
            'view': world.view,
            'macro': sample.macro,
            'p': character,
            'm': monsters,
            'x': [[x['unit_id'], x['txt_id'], x['mode'], *x['xy'], x['path']] for x in sample.missiles],
            'd': [[d.unit_id, d.txt_id, d.mode, d.x, d.y] for d in world.doors],
            'in': [*(sample.pointer or (None, None, None)), fx, fy, sorted(sample.keys)],
            'rect': list(sample.rect) if sample.rect else None,
        }
        if sample.tick is not None:
            line['k'] = sample.tick.hex()
        if character is not None and self.resists != self.written_resists:
            line['r'] = self.written_resists = list(self.resists)
        found = self.carried(sample)
        if character is not None:
            found['a'] = list(self.absorb)
            if self.life_frame is not None:
                found['sf'] = self.life_frame
        for key, value in found.items():
            if self.written.get(key) != value:
                line[key] = self.written[key] = value
        self.frames.write(json.dumps(line, separators=(',', ':')) + '\n')
        self.write_paths(clock, world.monsters)
        changed = self.states_changed(world.monsters)
        self.write_records(clock, sample, changed)
        if sample.macro_state is not None:
            state = dict(sample.macro_state)
            decision = state.pop('decision', None)
            if decision is not None and decision != self.decision:
                self.decision = decision
                self.event(clock, 'decision', **decision)
            if state != self.macro_state:
                self.macro_state = state
                self.event(clock, 'state', **state)
        if sample.census is not None:
            self.manifest.setdefault('census', []).append({'t': round(clock, 3), 'slots': sample.census})
            LOG.info('Combat take %s: unit table census %s', self.directory.name, sample.census)
        self.derive(clock, sample)
        self.restat(clock, world.monsters, changed)

    @staticmethod
    def carried(sample: Sample) -> dict[str, Any]:
        """What a frame holds only when it changes, of what the sample read (the module text)."""
        found: dict[str, Any] = {}
        if sample.things is not None:
            things = sorted(sample.things, key=lambda t: t.unit_id)
            found['o'] = [[t.unit_id, t.txt_id, t.mode, t.x, t.y, t.selectable] for t in things]
        if sample.states is not None:
            found['s'] = sample.states.hex()
        if sample.staff is not None:
            found['w'] = [sample.staff.charges, sample.staff.maximum, sample.staff.in_hand]
        elif sample.things is not None:
            found['w'] = None  # the slow reads were made and found no Teleport staff worn (or could not read it)
        if sample.belt is not None:
            found['b'] = list(sample.belt)
        if sample.hover_read:
            found['h'] = list(sample.hovered) if sample.hovered is not None else None
        player = sample.world.player
        if player is not None:
            found['f'] = list(player.buffs)
        if sample.loot is not None:
            drops = sorted(sample.loot.drops, key=lambda drop: drop.unit_id)
            items = sample.items
            found['g'] = [
                [d.unit_id, d.x, d.y, d.kind, d.label, *d.size, d.prized]
                # the item's code and quality (`item_identity`), where read
                + ([] if items is None else list(items.get(d.unit_id, (None, None))))
                for d in drops
            ]
            if sample.loot.room is not None:
                found['i'] = list(sample.loot.room)
        return found

    def states_changed(self, monsters) -> set[int]:
        """The monsters whose state words differ from the frame before they were last read in (a curse
        landed or ended); a unit's first words are no change."""
        changed = set()
        for m in monsters:
            if not m.states:
                continue
            before = self.unit_states.get(m.unit_id)
            if before is not None and before != m.states:
                changed.add(m.unit_id)
            self.unit_states[m.unit_id] = m.states
        return changed

    def restat(self, clock: float, monsters, changed: set[int]) -> None:
        """A `stats` event for each monster whose states changed and whose stat list now differs from the
        one written last (at first sight, in units.jsonl): a curse's effect on its resistances."""
        for m in monsters:
            if m.unit_id not in changed or not m.stats_at or m.mode in DEAD_MODES:
                continue
            stats = self.stats(m.stats_at)
            if stats and stats != self.unit_stats.get(m.unit_id):
                self.unit_stats[m.unit_id] = stats
                self.event(clock, 'stats', unit=m.unit_id, txt=m.txt_id, states=m.states.hex(), stats=stats)

    def write_records(self, clock: float, sample: Sample, changed: set[int] | frozenset[int] = frozenset()) -> None:
        """Research: the raw unit record of the character and of each monster the sample holds one for,
        at a change of its mode or of its states (`changed`) and once in RECORD_SECONDS (the module text)."""
        player = sample.world.player
        units = [(m.unit_id, m.mode, m.record, m.states, m.skill) for m in sample.world.monsters if m.record]
        if player is not None and player.record:
            units.append((player.unit_id, player.mode, player.record, b'', player.skill))  # its states: `s`
        rows = []
        for unit, mode, record, states, skill in units:
            before = self.recorded.get(unit)
            if before is None or before[0] != mode or unit in changed or clock - before[1] >= RECORD_SECONDS:
                self.recorded[unit] = (mode, clock)
                rows.append([unit, record.hex(), states.hex(), skill.hex()])
        if rows:
            line = {'t': round(clock, 3), 'n': self.count, 'u': rows}
            self.records.write(json.dumps(line, separators=(',', ':')) + '\n')

    def hurt(self, clock: float, sample: Sample, player: Player, life: int, max_life: int) -> None:
        """A `hurt` event when the character's life fell since the frame before (takes/hurts.py)."""
        foes = [
            hurts.Foe(
                m.unit_id, m.txt_id, m.flags, m.mode, m.x, m.y,
                hurts.target_unit(m.path) if m.path else None, self.mods.setdefault(m.unit_id, m.modifiers),
            )
            for m in sample.world.monsters
            if not m.ally and m.owner == NO_OWNER and m.mode not in DEAD_MODES
        ]  # fmt: skip
        flying = [(x['txt_id'], hurts.missile_point(x['path'])) for x in sample.missiles if len(x['path']) >= 16]
        companions = {
            m.unit_id: (m.txt_id, m.life, m.max_life) for m in sample.world.monsters if companion_of(m, player.unit_id)
        }
        before, self.before = (
            self.before,
            Before(player.unit_id, life, max_life, (player.x, player.y), foes, flying, self.absorb, companions),
        )
        if before is None or before.unit != player.unit_id or not max_life:
            return
        lost = hurts.lost(before.life, before.max_life, life, max_life)
        if lost < hurts.HURT_LEAST:
            return
        by = hurts.suspects(player.unit_id, before.at, [*before.foes, *foes])
        found = hurts.row(lost, life, max_life, by, hurts.beside(before.at, before.flying))
        # What else took of the blow: the ward's pool, and the mercenary's and the pets' life (a Health Link).
        found['absorb'] = [before.absorb[0], self.absorb[0], self.absorb[1]]
        found['companions'] = [
            [unit, txt, before.companions[unit][1] if unit in before.companions else None, now, most]
            for unit, (txt, now, most) in sorted(companions.items())
        ]
        if self.life_frame is not None:
            found['sf'] = self.life_frame
        self.event(clock, 'hurt', macro=sample.macro, resists=self.resists, **found)

    def write_paths(self, clock: float, monsters) -> None:
        """Research (combat/plan.md, monster movement): the whole path record of each monster that
        carries one (`combat_paths`), when it differs from the last one written past the position."""
        changed = [m for m in monsters if m.path and self.path_rest.get(m.unit_id) != m.path[8:]]
        if not changed:
            return
        self.path_rest.update((m.unit_id, m.path[8:]) for m in changed)
        row = {'t': round(clock, 3), 'n': self.count, 'm': [[m.unit_id, m.path.hex()] for m in changed]}
        self.paths.write(json.dumps(row, separators=(',', ':')) + '\n')

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
            if m.unit_id not in self.seen_units:
                self.seen_units.add(m.unit_id)
                unit: dict[str, Any] = {'t': round(clock, 3), 'unit': m.unit_id, 'txt': m.txt_id, 'flags': m.flags}
                stats = self.stats(m.stats_at)
                self.unit_stats[m.unit_id] = stats  # what a change of its states is told against (`restat`)
                unit.update(owner=m.owner, ally=m.ally, max_life=m.max_life, stats=stats)
                unit['mods'] = list(m.modifiers)
                self.units.write(json.dumps(unit) + '\n')
            if m.ally or m.owner != NO_OWNER:
                self.life[m.unit_id] = (m.txt_id, m.life)  # the pets and the mercenary: no hit or kill events
                continue
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
        for handle in (self.frames, self.events, self.units, self.missiles, self.paths, self.records):
            handle.close()
        duration = (self.last_clock - self.started) if self.started is not None and self.last_clock is not None else 0.0
        summary = {'frames': self.count, 'late_frames': self.late, 'seconds': round(duration, 3), 'events': self.counts}
        summary.update(monsters=len(self.seen_units), missiles=len(self.seen_missiles))
        self.manifest.update(finished_at=timestamp(), reason=reason, **summary)
        self.write_manifest()
        LOG.info('Combat take %s closed (%s): %s', self.directory.name, reason, summary)


class Recorder:
    """Per-frame logic: opens a take when the character is in a recorded level, closes it after IDLE_SECONDS
    elsewhere or on entering another recorded level (one take per stay, so a take matches one level map).
    `sample()` reads one frame or gives None when the game cannot be read."""

    def __init__(
        self,
        sample: Callable[[], Sample | None],
        *,
        output: Path,
        areas: frozenset[int] | None = AREAS,
        rate: float = FRAME_RATE,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        level: Callable[[], Level | None] | None = None,
        stats: Callable[[int], dict[int, int]] = lambda stats_at: {},
        manifest: Callable[[], dict[str, Any]] = dict,
        keep: int | None = None,
        town: bool = False,
        server_frame: Callable[[Player], int | None] | None = None,
    ) -> None:
        """`areas`: the levels recorded (None: every non-town level; `town` adds towns). `keep`: the bytes the takes
        under `output` are held to, each packed as it closes (takes/retain.py; None: as written). `server_frame`:
        reads `sf` (None: not read)."""
        self.sample, self.output, self.areas, self.rate = sample, output, areas, rate
        self.keep, self.town, self.server_frame = keep, town, server_frame
        self.last: tuple[str, str] | None = None  # (game, take) of the take opened last
        self.clock, self.sleep, self.level, self.stats, self.manifest = clock, sleep, level, stats, manifest
        self.take: Take | None = None
        self.away_since: float | None = None  # when the character was last seen outside the areas
        self.takes = 0
        self.level_at = -math.inf  # when the guide's level was last looked at for the take
        self.tidying: threading.Thread | None = None  # the packing of the take closed last
        self.noted: list[tuple[float, str, dict[str, Any]]] = []  # the macro's word since the last frame
        self.noting = threading.Lock()
        # The service's own inputs since the last frame (`sent`): appended on the sending thread, taken here.
        self.inputs: collections.deque[tuple[float, str, tuple[int, ...], str, str | None]] = collections.deque(
            maxlen=SENT_MOST
        )
        self.routine: Callable[[], str | None] | None = None  # the macro run's routine (the service sets it)

    def note(self, kind: str, **fields: Any) -> None:
        """An event of somebody else's (the macro runner's `request` and `said`), from any thread: kept
        with its own clock and written with the next frame of a take."""
        with self.noting:
            self.noted.append((self.clock(), kind, fields))

    def sent(self, kind: str, what: tuple[int, ...]) -> None:
        """input/sent.py's listener, on the sending thread: a lock-free deque append (an input never waits for a
        frame being written) with the clock, the thread and its routine; `step` writes it."""
        by = threading.current_thread().name
        routine = self.routine() if by == 'macro' and self.routine is not None else None
        self.inputs.append((self.clock(), kind, what, by, routine))

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
            and (player.area in self.areas if self.areas is not None else self.town or player.area not in TOWN_IDS)
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
            with self.noting:
                noted, self.noted = self.noted, []
            for at, kind, fields in noted:
                self.take.event(at, kind, **fields)
            for _ in range(len(self.inputs)):  # only this thread takes from the left
                self.take.sent(*self.inputs.popleft(), sample.rect)
            self.take.frame(now, sample, late)
        else:
            # No take to write them in: kept, so the next take begins with what was asked and said on the way in.
            with self.noting:
                self.noted = [note for note in self.noted if now - note[0] <= NOTE_SECONDS][-NOTE_MOST:]
            while self.inputs and now - self.inputs[0][0] > NOTE_SECONDS:
                self.inputs.popleft()

    def open(self, now: float, sample: Sample, area: int) -> None:
        self.takes += 1
        player = sample.world.player
        name = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + f'-{area}'
        manifest = {
            'started_at': timestamp(), 'area': area, 'rate': self.rate, 'schema': SCHEMA,
            'clock': {'monotonic': round(now, 3), 'wall': round(time.time(), 3)}, 'game': sample.world.game_name,
            'previous': self.last[1] if self.last is not None and self.last[0] == sample.world.game_name else None,
            'character': player.name if player else None,
            'slots': list(sample.world.slots), 'left_skill': player.left_skill if player else None,
            'right_skill': player.right_skill if player else None, **self.manifest(),
        }  # fmt: skip
        if player is not None and player.stats_at:
            manifest['character_stats'] = {str(stat): value for stat, value in self.stats(player.stats_at).items()}
        self.last = (sample.world.game_name, name)
        self.take = Take(self.output / name, manifest, self.stats, self.server_frame)
        self.write_level(self.take, now)
        LOG.info('Combat take %s opened in area %d', name, area)

    def close(self, reason: str) -> None:
        if self.take is not None:
            self.write_level(self.take, self.clock())  # the walls read while the take ran
            self.take.close(reason)
            closed, self.take = self.take.directory, None
            if self.keep is not None:
                # Off this thread: packing a long take takes a second, and the next take may open at once.
                work = threading.Thread(target=retain.tidy, args=(self.output, closed, self.keep), daemon=True)
                work.start()
                self.tidying = work
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
        self,
        macro_working: Callable[[], bool] = lambda: False,
        clock: Callable[[], float] = time.monotonic,
        *,
        paths: bool = False,
        loot: Callable[[GameMemory], Loot] | None = None,
        macro_state: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.paths = paths  # also read each monster's whole path record (movement research)
        # the pickup step's own read of the ground, the belt and the inventory, with its settings
        self.loot = loot
        self.macro_state = macro_state
        self.memory: GameMemory | None = None
        self.bound: tuple[int, int, int] | None = None
        self.keys = None
        self.macro_working = macro_working
        self.clock = clock
        self.lock = threading.Lock()
        self.key_names: dict[int, str] = {}
        self.census_at = -math.inf
        self.slow_at = -math.inf
        self.slow: tuple[Any, ...] = (None,) * 6  # things, staff, belt, loot, macro state, drops' items: as read last
        self.items: dict[int, tuple[str | None, int | None]] = {}  # drop unit id -> (code, quality), read once
        self.life_block: tuple[int, int] | None = None  # (player data, the block its LIFE_BLOCK points to)

    def attach(self, pid: int, base: int, table: int) -> None:
        if self.bound == (pid, base, table):
            return
        with self.lock:
            if self.memory is not None:
                self.memory.close()
            self.memory = GameMemory(pid, base, table)
            self.bound = (pid, base, table)
            self.items, self.life_block = {}, None

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

    def server_frame(self, player: Player) -> int | None:
        """The server frame of the character's last life message (LIFE_FRAME); None when unread. The block
        pointer is kept for the player data it was read through: one read a call after the first."""
        with self.lock:
            memory = self.memory
            if memory is None or len(player.record) < PLAYER_DATA + 8:
                return None
            try:
                data = struct.unpack_from('<Q', player.record, PLAYER_DATA)[0]
                if not data:
                    return None
                if self.life_block is None or self.life_block[0] != data:
                    self.life_block = (data, struct.unpack('<Q', memory.read(data + LIFE_BLOCK, 8))[0])
                block = self.life_block[1]
                return struct.unpack('<I', memory.read(block + LIFE_FRAME, 4))[0] if block else None
            except OSError, ValueError, struct.error:
                self.life_block = None
                return None

    def identify(self, memory: GameMemory, loot: Loot | None) -> dict[int, tuple[str | None, int | None]] | None:
        """(code, quality) of each drop of `loot` (`item_identity`), read once a drop: kept while it lies
        there, read again only when the first read found nothing."""
        if loot is None:
            return None
        found = {}
        for drop in loot.drops:
            known = self.items.get(drop.unit_id)
            if known is None or known[0] is None:
                known = item_identity(memory.read, memory.table, drop.unit_id)
            found[drop.unit_id] = known
        self.items = found
        return found

    def __call__(self) -> Sample | None:
        with self.lock:
            memory = self.memory
            if memory is None:
                return None
            census = None
            try:
                world = memory.world()
                if world.in_game and world.player is not None:
                    world = dataclasses.replace(world, monsters=memory.all_monsters(paths=self.paths, records=True))
                missiles = memory.missiles() if world.in_game else []
                if world.in_game and self.clock() - self.census_at >= CENSUS_SECONDS:
                    self.census_at = self.clock()
                    census = memory.census()
                states = None
                tick = memory.tick() if world.in_game else None
                hovered = memory.hovered() if world.in_game else None
                if world.in_game and world.player is not None:
                    states = memory.states(world.player.stats_at)
                    if self.clock() - self.slow_at >= SLOW_SECONDS:
                        self.slow_at = self.clock()
                        loot = self.loot(memory) if self.loot is not None else None
                        # one walk of the items, not two; a belt with an item unread is not written
                        belt = memory.belt() if loot is None else loot.belt if loot.belt_read else None
                        state = self.macro_state() if self.macro_state is not None else None
                        items = self.identify(memory, loot)
                        self.slow = (memory.operated(), memory.teleport(), belt, loot, state, items)
            except (OSError, ValueError) as exc:
                LOG.debug('Combat recorder: read failed (%s)', exc)
                return None
        pointer = rect = None
        keys: frozenset[int] = frozenset()
        if self.keys is not None:
            pointer, rect, keys = self.keys.pointer_state(), self.keys.focused_window_rect(), self.keys.held_keys()
        things, staff, belt, loot, state, items = self.slow
        return Sample(
            world, missiles, pointer, rect, keys, self.macro_working(), census,
            things, states, staff, belt, loot, state, tick, hovered, world.in_game, items,
        )  # fmt: skip


class MacroLines(logging.Handler):
    """Every line the macro logs ('Macro: ...', 'Macro stopped: ...') as a `log` note of the recorder's."""

    def __init__(self, note: Callable[..., None]) -> None:
        super().__init__(logging.INFO)
        self.note = note

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = record.getMessage()
        except Exception:  # a line that cannot be formatted is the logger's to report, not the recorder's
            return
        if text.startswith('Macro'):
            self.note('log', level=record.levelname, text=text)


class CombatRecorder:
    """The service's handle: `poll` binds the game, the thread records."""

    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        output: Path,
        areas: frozenset[int] | None = AREAS,
        rate: float = FRAME_RATE,
        level: Callable[[], Level | None] | None = None,
        macro_working: Callable[[], bool] = lambda: False,
        poll_interval: float = 1.0,
        paths: bool = False,
        keep: int | None = None,
        town: bool = False,
        loot: Callable[[GameMemory], Loot] | None = None,
        macro_state: Callable[[], dict[str, Any]] | None = None,
        code: dict[str, Any] | None = None,
    ) -> None:
        self.source, self.capture_lock = source, capture_lock
        self.sampler = LiveSampler(macro_working, paths=paths, loot=loot, macro_state=macro_state)
        self.recorder = Recorder(
            self.sampler, output=output, areas=areas, rate=rate, level=level, stats=self.sampler.stats,
            manifest=lambda: {
                'keys': {str(key): name for key, name in self.sampler.name_keys().items()},
                'code': code or {},
                'input_mode': self.input_mode() if self.input_mode is not None else None,
                'switch_interval': sys.getswitchinterval(),
            },
            keep=keep, town=town, server_frame=self.sampler.server_frame,
        )  # fmt: skip
        # The game's input mode when a take opens ('keyboard', 'controller', None: unread), set by the service
        # (tracking/input_mode.py InputModeWatch, which also notes each flip as an `input_mode` event).
        self.input_mode: Callable[[], str | None] | None = None
        self.listener = MacroLines(self.recorder.note)
        LOG.addHandler(self.listener)
        sent.listen(self.recorder.sent)  # every input this process sends: a `sent` event (input/sent.py)
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
            table = one_unit_table(self.source.capture)
            if table is None:
                raise ValueError('the game is not attached')
            self.sampler.attach(self.source.pid, self.source.images['candidate_base'], table)
            self.warned = False
        except Exception as exc:
            self.sampler.detach()
            if not self.warned:
                LOG.info('Combat recorder: waiting for the game (%s)', exc)
                self.warned = True
        finally:
            self.capture_lock.release()

    def close(self) -> None:
        LOG.removeHandler(self.listener)
        if sent.listener == self.recorder.sent:
            sent.listen(None)
        self.stop.set()
        self.thread.join(timeout=3)
        self.sampler.detach()
