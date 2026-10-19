"""The game's input method, read only: keyboard and mouse, or controller (rca/2026-10-13/controller-mode.md).

The client keeps the mode in one byte and asks for a flip by setting a flag on its panel manager; the flip is
a reload of the whole interface, done a moment later (native/layout.py CONTROLLER_MODE_RVA). Both are read here:

- `read_input_mode`: the mode, whether a flip is pending, and to which mode;
- `Flips`: from successive readings, each flip with its duration (asked -> byte changed -> reload done), logged
  and given to the combat take, so the time of a flip is measured in every game (gamepad-proton.md step 5);
- `read_bindings`: the controller records the game loaded at game entry (what a file write gave);
- `read_controller`: in controller mode, the client's own target and the pressed record and skill;
- `InputModeWatch`: all of it on a thread of `make serve`, at `rate` reads a second with its own memory handle,
  bound to the game by `poll` from the service loop. Nothing is ever written.
"""

import logging
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from inventory_tracking.models import InputMode, Observation
from inventory_tracking.native.layout import (
    CONTROLLER_MODE_RVA,
    CTL_BINDINGS_RVA,
    CTL_PRESSED_RECORD,
    CTL_PRESSED_SKILL,
    CTL_RECORD,
    CTL_RECORDS,
    CTL_STATE_RVA,
    CTL_STATE_STRIDE,
    CTL_TARGET,
    PANEL_MANAGER_RVA,
    PANEL_PENDING,
    PANEL_WANTED,
    PLAYER_SLOT_RVA,
)
from inventory_tracking.native.memory import ProcessMemory


LOG = logging.getLogger(__name__)

Read = Callable[[int, int], bytes]  # (address, size) -> bytes of the game's memory
PRESS_WINDOW = 5.0  # seconds: a pad press this long before a flip is taken as what asked for it
BINDINGS_SECONDS = 3.0  # between two reads of the loaded bindings
UNIT_SPAN = 0x10  # a unit's type, class, id and mode (native/units.py)
MAX_SLOT = 7


def read_input_mode(read: Read, base: int) -> InputMode:
    """The mode byte and the panel manager's flip flag; ValueError when the byte is neither 0 nor 1."""
    mode = read(base + CONTROLLER_MODE_RVA, 1)[0]
    if mode not in (0, 1):
        raise ValueError(f'input mode byte reads {mode}')
    manager = struct.unpack('<Q', read(base + PANEL_MANAGER_RVA, 8))[0]
    if not manager:
        return InputMode(mode == 1)
    flags = read(manager + PANEL_PENDING, PANEL_WANTED - PANEL_PENDING + 1)
    pending, wanted = flags[0], flags[PANEL_WANTED - PANEL_PENDING]
    if pending != 1:
        return InputMode(mode == 1)
    return InputMode(mode == 1, True, wanted == 1)


def observe_input_mode(pid: int, images: dict) -> Observation[InputMode]:
    """One reading for the OSD's reader (tracking/reader.py), with its own short-lived handle."""
    sampled = time.monotonic()
    try:
        with ProcessMemory(pid) as memory:
            return Observation(sampled, read_input_mode(memory.pread, images['candidate_base']))
    except (OSError, ValueError, KeyError, struct.error, IndexError) as exc:
        return Observation.unavailable(sampled, str(exc))


def read_bindings(read: Read, base: int) -> tuple[int, ...]:
    """The skill of each of the 32 controller records the game holds (-1: none)."""
    data = read(base + CTL_BINDINGS_RVA, CTL_RECORD * CTL_RECORDS)
    return tuple(struct.unpack_from('<i', data, CTL_RECORD * at)[0] for at in range(CTL_RECORDS))


@dataclass(frozen=True)
class ControllerState:
    """The client's controller target and the button being pressed, for the local player's slot."""

    target: tuple[int, int] | None  # (unit type, unit id) of the client's target; None: none
    record: int  # the pressed button's record (-1: none)
    skill: int  # its skill (-1: none)

    def fields(self) -> dict[str, Any]:
        return {'target': list(self.target) if self.target else None, 'record': self.record, 'skill': self.skill}


def read_controller(read: Read, base: int) -> ControllerState:
    slot = struct.unpack('<I', read(base + PLAYER_SLOT_RVA, 4))[0]
    if slot > MAX_SLOT:
        raise ValueError(f'player slot reads {slot}')
    state = base + CTL_STATE_RVA + CTL_STATE_STRIDE * slot
    pointer = struct.unpack('<Q', read(state + CTL_TARGET, 8))[0]
    target = None
    if pointer > 0x10000:
        unit_type, _, unit_id = struct.unpack('<III', read(pointer, 12))
        target = (unit_type, unit_id)
    record, skill = struct.unpack('<ii', read(state + CTL_PRESSED_RECORD, 4) + read(state + CTL_PRESSED_SKILL, 4))
    return ControllerState(target, record, skill)


def milliseconds(seconds: float | None) -> int | None:
    return None if seconds is None else round(1000 * seconds)


class Flips:
    """Turns readings into flips: each with the time from the ask (the flag going up) to the byte changing
    and to the reload being done (the flag down), and from the last pad press when there was one. A flip
    faster than one reading has no ask: its times are then from the press, or "within one reading"."""

    def __init__(
        self,
        pressed: Callable[[], float | None] = lambda: None,
        noted: Callable[..., None] = lambda kind, **fields: None,
    ) -> None:
        self.pressed, self.noted = pressed, noted
        self.mode: InputMode | None = None
        self.asked_at: float | None = None
        self.switched_at: float | None = None
        self.seen_at: float | None = None  # the reading before this one
        self.flips = 0
        self.last_ms: int | None = None  # the last flip's whole duration

    def see(self, now: float, mode: InputMode | None) -> dict[str, Any] | None:
        """Take one reading (None: the game cannot be read); the flip that ended with it, if one did."""
        before, self.mode = self.mode, mode
        previous_at, self.seen_at = self.seen_at, now
        if mode is None:
            self.asked_at = self.switched_at = None
            return None
        if before is None:
            self.noted('input_mode', mode=mode.name, pending=mode.pending)
            if mode.pending:
                self.asked_at = now
            return None
        if mode.pending and not before.pending:
            self.asked_at = now
            self.noted('input_mode', mode=mode.name, pending=True, wanted='controller' if mode.wanted else 'keyboard')
        if mode.controller != before.controller:
            self.switched_at = now  # with no ask seen, the whole flip fell between two readings
        if mode.pending:
            return None
        if before.pending or mode.controller != before.controller:
            return self.finish(now, mode, previous_at)
        return None

    def finish(self, now: float, mode: InputMode, previous_at: float | None) -> dict[str, Any]:
        asked, switched = self.asked_at, self.switched_at
        self.asked_at = self.switched_at = None
        pressed = self.pressed()
        start = asked if asked is not None else previous_at
        if pressed is not None and (start is None or not 0 <= start - pressed <= PRESS_WINDOW):
            pressed = None
        changed = switched is not None
        flip = {
            'from': ('keyboard' if mode.controller else 'controller') if changed else mode.name,
            'to': mode.name,
            'changed': changed,
            'switched_ms': milliseconds(switched - asked) if changed and asked is not None else None,
            'done_ms': milliseconds(now - asked) if asked is not None else None,
            'from_press_ms': milliseconds(now - pressed) if pressed is not None else None,
            'press_before_ask_ms': milliseconds(asked - pressed) if pressed is not None and asked is not None else None,
            'within_ms': milliseconds(now - previous_at) if asked is None and previous_at is not None else None,
        }
        if changed:
            self.flips += 1
            self.last_ms = flip['done_ms'] if flip['done_ms'] is not None else flip['from_press_ms']
        self.noted('input_mode', mode=mode.name, pending=False, flip=flip)
        LOG.info('%s', describe(flip))
        return flip


def describe(flip: dict[str, Any]) -> str:
    if not flip['changed']:
        head = f'Input mode: the panels were reloaded, still {flip["to"]}'
    else:
        head = f'Input mode: {flip["from"]} -> {flip["to"]}'
    parts = []
    if flip['switched_ms'] is not None:
        parts.append(f'switched {flip["switched_ms"]} ms after the ask')
    if flip['done_ms'] is not None:
        parts.append(f'panels ready at {flip["done_ms"]} ms')
    if flip['within_ms'] is not None:
        parts.append(f'within one reading ({flip["within_ms"]} ms)')
    if flip['from_press_ms'] is not None:
        before = flip['press_before_ask_ms']
        parts.append(
            f'{flip["from_press_ms"]} ms from the pad press'
            + (f' ({before} ms before the ask)' if before is not None else '')
        )
    return head + (': ' + ', '.join(parts) if parts else '')


class InputModeWatch:
    """The input mode for `make serve`: read `rate` times a second on its own thread, flips logged and noted
    (`noted`: the combat recorder's `note`), the controller's target and pressed skill noted on change in
    controller mode, the loaded bindings logged on change. `current` is the last reading (None: unreadable).
    `poll(now)` from the service loop binds it to the game `source` has attached."""

    def __init__(
        self,
        source,
        *,
        rate: float = 100.0,
        pressed: Callable[[], float | None] = lambda: None,
        noted: Callable[..., None] = lambda kind, **fields: None,
        names: Callable[[tuple[int, ...]], str] | None = None,
        clock: Callable[[], float] = time.monotonic,
        poll_interval: float = 1.0,
        start: bool = True,
    ) -> None:
        self.source, self.rate, self.clock, self.poll_interval = source, rate, clock, poll_interval
        self.noted = noted
        self.names = names
        self.flips = Flips(pressed, noted)
        self.current: InputMode | None = None
        self.controller: ControllerState | None = None
        self.bindings: tuple[int, ...] | None = None
        self.bindings_at = -float('inf')
        self.bound: tuple[int, int] | None = None
        self.memory = ProcessMemory()
        self.last_poll = -float('inf')
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name='input-mode', daemon=True)
        if start:
            self.thread.start()

    def poll(self, now: float) -> None:
        if now - self.last_poll < self.poll_interval:
            return
        self.last_poll = now
        try:
            target = (self.source.pid, self.source.images['candidate_base'])
        except AttributeError, KeyError, TypeError:
            target = None
        with self.lock:
            if target == self.bound:
                return
            self.close_memory()
            if target is not None:
                try:
                    self.memory.bind(target[0])
                    self.bound = target
                except OSError as exc:
                    LOG.info('Input mode: the game memory cannot be read (%s)', exc)

    def close_memory(self) -> None:
        self.memory.close()
        self.bound, self.bindings = None, None

    def read(self, address: int, size: int) -> bytes:
        data = self.memory.pread(address, size)
        if len(data) != size:
            raise OSError(f'{len(data)} of {size} bytes at {address:#x}')
        return data

    def step(self, now: float) -> None:
        """One reading."""
        with self.lock:
            if self.memory.fd is None or self.bound is None:
                mode = None
            else:
                base = self.bound[1]
                try:
                    mode = read_input_mode(self.read, base)
                    if now - self.bindings_at >= BINDINGS_SECONDS:
                        self.bindings_at = now
                        self.see_bindings(read_bindings(self.read, base))
                    self.see_controller(read_controller(self.read, base) if mode.controller else None)
                except OSError, ValueError, struct.error, IndexError:
                    mode = None
        self.current = mode
        self.flips.see(now, mode)

    def see_bindings(self, skills: tuple[int, ...]) -> None:
        if skills == self.bindings:
            return
        self.bindings = skills
        # Records 0-11 are the pad's buttons, 12-15 reached by keyboard skill keys only, 16-27 the second weapon
        # set's with "Controller Weapon Swap Separate Bindings" (rca/2026-10-13/controller-gaps.md section 2).
        if any(skill != -1 for skill in skills[:28]):
            said = self.names(skills) if self.names is not None else ', '.join(map(str, skills[:28]))
            LOG.info('Controller bindings loaded: %s', said)

    def see_controller(self, state: ControllerState | None) -> None:
        if state == self.controller:
            return
        self.controller = state
        if state is not None:
            self.noted('ctl', **state.fields())

    def run(self) -> None:
        period = 1 / self.rate
        while not self.stop.is_set():
            try:
                self.step(self.clock())
            except Exception:
                LOG.exception('Input mode: a reading failed')
            self.stop.wait(period)

    def close(self) -> None:
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
        with self.lock:
            self.close_memory()
