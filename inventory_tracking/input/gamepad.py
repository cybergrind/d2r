"""A virtual gamepad the game sees as an Xbox 360 pad: a kernel uinput device, made with plain ioctls.

Begun as an experiment (2026-10-13, rca/2026-10-13/pickup-cube.md, "Design C": Loot to Cube exists only in
controller mode); now the pad the macros are to play controller mode with (rca/2026-10-13/controller-mode.md).
The service's own input is XTest (keyboard.py), which has no pad, hence this device. The game takes it through
Proton (SDL -> XInput); its first press only flips the client into controller mode (that press is thrown away).

The device exists while the `Pad` is open, and is kept for the session: unplugged in controller mode the game
shows a reconnect panel. `/dev/uinput` must be there (`modprobe uinput`) and writable by the user; `problem()`
says which of the two is missing and the command that mends it.

The controller bindings (`bind_table`) are the game's `.ctlo`/`.ctl` file of a character: written only while
D2R.exe is closed (the client reads the file once at launch and writes it back on leaving a game).
"""

import contextlib
import fcntl
import logging
import os
import re
import shutil
import struct
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path


LOG = logging.getLogger(__name__)

DEVICE = Path('/dev/uinput')
NAME = b'Microsoft X-Box 360 pad'
BUS_USB, VENDOR, PRODUCT, VERSION = 0x03, 0x045E, 0x028E, 0x0110
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
# linux/input-event-codes.h
BUTTONS = {
    'a': 0x130,
    'b': 0x131,
    'x': 0x133,
    'y': 0x134,
    'lb': 0x136,
    'rb': 0x137,
    'back': 0x13A,
    'start': 0x13B,
    'guide': 0x13C,
    'ls': 0x13D,
    'rs': 0x13E,
}
ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ, ABS_HAT0X, ABS_HAT0Y = 0, 1, 2, 3, 4, 5, 16, 17
# axis -> (least, most): the sticks, the triggers, the directional pad
AXES = {
    ABS_X: (-32768, 32767),
    ABS_Y: (-32768, 32767),
    ABS_Z: (0, 255),
    ABS_RX: (-32768, 32767),
    ABS_RY: (-32768, 32767),
    ABS_RZ: (0, 255),
    ABS_HAT0X: (-1, 1),
    ABS_HAT0Y: (-1, 1),
}
TRIGGERS = {'lt': ABS_Z, 'rt': ABS_RZ}
# The directional pad: (axis, value). On the game's controller bar each belt cell has a d-pad hint (2026-10-13).
DPAD = {'up': (ABS_HAT0Y, -1), 'down': (ABS_HAT0Y, 1), 'left': (ABS_HAT0X, -1), 'right': (ABS_HAT0X, 1)}
# The sticks' axes, (x, y). Linux's convention, as the xpad driver reports a real pad: y grows downward, so a
# stick pushed up is negative y (SDL and Wine turn it into XInput's up-positive). Screen directions are given
# here: (1, 0) right, (0, -1) up. Not yet seen in the game (controller-mode.md, plan step 8).
STICKS = {'left': (ABS_X, ABS_Y), 'right': (ABS_RX, ABS_RY)}
STICK_MOST = 32767
TRIGGER_MOST = 255
# linux/uinput.h
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT = 0x40045564, 0x40045565, 0x40045567
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
ABS_COUNT = 64
HOLD = 0.08  # seconds a tapped button stays down: two of the game's frames and more
SETTLE = 1.0  # seconds after the device appears before Wine has it as a pad (a guess; the experiment tells)
# The game's controller records: 0-5 the buttons A X B Y RB RT, 6-11 the same with LT held
# (controllersettings.json `controllerSkillButtonMapping`, read 2026-10-13).
RECORD_BUTTONS = ('a', 'x', 'b', 'y', 'rb', 'rt')
MODIFIER = 'lt'


def names() -> frozenset[str]:
    """Every name a `Pad` presses: buttons, triggers, d-pad directions."""
    return frozenset(BUTTONS) | frozenset(TRIGGERS) | frozenset(DPAD)


def record_buttons(record: int) -> tuple[str, ...]:
    """The pad names to hold for a controller record (0-11): ('y',) for 3, ('lt', 'y') for 9."""
    if not 0 <= record < 2 * len(RECORD_BUTTONS):
        raise ValueError(f'record {record} has no button')
    button = RECORD_BUTTONS[record % len(RECORD_BUTTONS)]
    return (MODIFIER, button) if record >= len(RECORD_BUTTONS) else (button,)


def record_label(record: int) -> str:
    """'Y', 'LT+Y'; records 16-27 are the same buttons for the other weapon set."""
    if 16 <= record < 16 + 2 * len(RECORD_BUTTONS):
        return record_label(record - 16) + ' (other weapons)'
    if not 0 <= record < 2 * len(RECORD_BUTTONS):
        return f'record {record}'
    return '+'.join(name.upper() for name in record_buttons(record))


def problem() -> str | None:
    """Why a pad cannot be made here, with the command that mends it; None when it can."""
    if not DEVICE.exists():
        return f'{DEVICE} is not there: `sudo modprobe uinput`'
    if not os.access(DEVICE, os.W_OK):
        return f'{DEVICE} is not writable by this user: `sudo setfacl -m u:{os.getuid()}:rw {DEVICE}`'
    return None


# A character's controller bindings (`<name><digits>.ctlo` online, `<name>.ctl` offline, beside its key
# file): 4 bytes of version, then 32 records of 7 little-endian int32: the skill (-1: none), a resolved value
# (-1), the hand in the low byte of the third (1 left, 0 right; its upper bytes are padding), then 4, 0xFF, 0, 0
# (loot-to-cube-mouse.md section 2).
LOOT = 358
TOWN_PORTAL = 359
SWAP_WEAPONS = 361
LOOT_TO_CUBE = 370  # skills.txt `CubeLoot`
HEAD, RECORD, SLOTS = 4, 28, 32
# skills.txt `leftskill` of the skills a record may get (read 2026-10-13): the hand byte the client's own
# default fill writes. Any other skill gets 0 (right).
LEFT_HANDED = frozenset((0, 375, 379, 388, 390, 393, 395))
SKILL_NAMES = {
    0: 'Attack',
    54: 'Teleport',
    357: 'Interact',
    LOOT: 'Loot',
    TOWN_PORTAL: 'Town Portal',
    360: 'Emote Wheel',
    SWAP_WEAPONS: 'Swap Weapons',
    362: 'Map',
    363: 'Show Items',
    364: 'Run Toggle',
    LOOT_TO_CUBE: 'Loot to Cube',
    395: 'Miasma Bolt',
}


def skill_name(skill: int, more: Mapping[int, str] | None = None) -> str:
    return (more or {}).get(skill) or SKILL_NAMES.get(skill) or f'skill {skill}'


def legend(skills: Iterable[int], more: Mapping[int, str] | None = None) -> str:
    """'A Attack, X Loot to Cube, ...' for records 0-11 that hold a skill."""
    return ', '.join(
        f'{record_label(record)} {skill_name(skill, more)}'
        for record, skill in enumerate(list(skills)[:12])
        if skill != -1
    )


def bindings_file(saved_games: Path, name: str) -> Path | None:
    pattern = re.compile(re.escape(name) + r'\d*\.ctlo?')
    try:
        found = [path for path in saved_games.iterdir() if pattern.fullmatch(path.name)]
    except OSError:
        return None
    return max(found, key=lambda path: path.stat().st_mtime) if found else None


def used(skills: list[int]) -> str:
    return ', '.join(f'{at}: {skill}' for at, skill in enumerate(skills) if skill != -1)


def bind_table(
    saved_games: Path,
    name: str,
    table: Mapping[int, int],
    keep: Path,
    overwrite: Iterable[int] = (),
    stamp: Callable[[], str] = lambda: time.strftime('%Y%m%dT%H%M%S'),
    names: Mapping[int, str] | None = None,
) -> list[str]:
    """Write `table` (record -> skill) into `name`'s controller bindings; what was done, a line each.

    A record gets its skill when it is empty, or holds another skill and is named in `overwrite`. A record
    that holds another skill and is not named is the player's and is left alone; a skill the file already
    has on another record is not written twice. The file as it was is copied into `keep` before the first
    change, and nothing is written when that copy cannot be made. Call it only while D2R.exe is closed.
    `names`: skill names beyond SKILL_NAMES, for the lines."""
    path = bindings_file(saved_games, name)
    if path is None:
        return [f'no controller bindings of {name} in {saved_games}']
    data = bytearray(path.read_bytes())
    if len(data) != HEAD + RECORD * SLOTS:
        return [f'{path.name} is {len(data)} bytes, not {HEAD + RECORD * SLOTS}: not touched']
    skills = [struct.unpack_from('<i', data, HEAD + RECORD * at)[0] for at in range(SLOTS)]
    overwrite = frozenset(overwrite)
    said, changes = [], []
    for record, skill in sorted(table.items()):
        if not 0 <= record < SLOTS:
            said.append(f'{path.name}: record {record} is none of {SLOTS}: skipped')
            continue
        if skills[record] == skill:
            continue
        if skill in skills:
            said.append(
                f'{path.name}: {skill_name(skill, names)} is on record {skills.index(skill)} already, '
                f'not put on {record}'
            )
            continue
        if skills[record] != -1 and record not in overwrite:
            said.append(
                f'{path.name}: record {record} holds {skill_name(skills[record], names)} (set by the player), '
                f'{skill_name(skill, names)} not written'
            )
            continue
        changes.append((record, skills[record], skill))
        skills[record] = skill
    if not changes:
        return [*said, f'{path.name}: nothing to write (records in use: {used(skills)})']
    keep.mkdir(parents=True, exist_ok=True)
    copy = keep / f'{path.name}.{stamp()}'
    shutil.copy2(path, copy)
    # The padding of the hand field as the file's first record has it.
    padding = struct.unpack_from('<i', data, HEAD + 8)[0] & ~0xFF
    for record, before, skill in changes:
        row = (skill, -1, padding | (1 if skill in LEFT_HANDED else 0), 4, 0xFF, 0, 0)
        struct.pack_into('<7i', data, HEAD + RECORD * record, *row)
        was = 'empty' if before == -1 else skill_name(before, names)
        said.append(f'{path.name}: record {record} ({record_label(record)}) {was} -> {skill_name(skill, names)}')
    path.write_bytes(data)
    return [*said, f'{path.name}: written (the file as it was: {copy})']


class Pad:
    """The device, from `Pad()` to `close()`: buttons, triggers, d-pad and sticks, held or tapped."""

    def __init__(self, sleep=time.sleep, clock=time.monotonic, open_device=None) -> None:
        self.sleep, self.clock = sleep, clock
        self.made_at = clock()
        self.down: set[str] = set()  # names held now (buttons, triggers, d-pad directions)
        self.pressed_at: float | None = None  # when the last `press` sent its first input
        self.sticks: dict[str, tuple[float, float]] = {'left': (0.0, 0.0), 'right': (0.0, 0.0)}
        self.file = (open_device or self.create)()

    @staticmethod
    def create() -> int:
        file = os.open(DEVICE, os.O_WRONLY | os.O_NONBLOCK)
        try:
            for kind in (EV_SYN, EV_KEY, EV_ABS):
                fcntl.ioctl(file, UI_SET_EVBIT, kind)
            for code in BUTTONS.values():
                fcntl.ioctl(file, UI_SET_KEYBIT, code)
            least, most = [0] * ABS_COUNT, [0] * ABS_COUNT
            for axis, (low, high) in AXES.items():
                fcntl.ioctl(file, UI_SET_ABSBIT, axis)
                least[axis], most[axis] = low, high
            # struct uinput_user_dev: the name, the id, ff_effects_max, then absmax, absmin, absfuzz, absflat
            setup = struct.pack('80sHHHHI', NAME, BUS_USB, VENDOR, PRODUCT, VERSION, 0)
            setup += struct.pack(f'{ABS_COUNT}i', *most) + struct.pack(f'{ABS_COUNT}i', *least)
            setup += bytes(4 * ABS_COUNT * 2)
            os.write(file, setup)
            fcntl.ioctl(file, UI_DEV_CREATE)
        except OSError:
            os.close(file)
            raise
        return file

    def event(self, kind: int, code: int, value: int) -> None:
        os.write(self.file, struct.pack('llHHi', 0, 0, kind, code, value))

    def report(self) -> None:
        self.event(EV_SYN, 0, 0)

    def settle(self) -> None:
        """The first input waits until Wine has had the device for SETTLE seconds."""
        waited = SETTLE - (self.clock() - self.made_at)
        if waited > 0:
            self.sleep(waited)

    def _set(self, name: str, down: bool) -> None:
        if name in TRIGGERS:
            self.event(EV_ABS, TRIGGERS[name], TRIGGER_MOST if down else 0)
        elif name in DPAD:
            axis, value = DPAD[name]
            other = [d for d in self.down if d in DPAD and d != name and DPAD[d][0] == axis]
            self.event(EV_ABS, axis, value if down else 0)
            for name_on_axis in other:  # the opposite direction on the same axis is let go
                self.down.discard(name_on_axis)
        elif name in BUTTONS:
            self.event(EV_KEY, BUTTONS[name], 1 if down else 0)
        else:
            raise ValueError(f'no pad input named {name!r}')
        (self.down.add if down else self.down.discard)(name)

    def press(self, *names: str) -> None:
        """Press the named inputs in order (one report each, so 'lt' is down before the button)."""
        self.settle()
        self.pressed_at = self.clock()
        for name in names:
            self._set(name, True)
            self.report()

    def release(self, *names: str) -> None:
        """Let the named inputs go, in reverse order."""
        for name in reversed(names):
            self._set(name, False)
            self.report()

    def tap(self, button: str, hold: float = HOLD) -> None:
        """Press `button` and let it go: one of BUTTONS, a trigger ('lt', 'rt') or a d-pad direction."""
        self.combo(button, hold=hold)

    def combo(self, *names: str, hold: float = HOLD) -> None:
        """Press `names` in order, hold, release in reverse: ('lt', 'y') casts record 9."""
        self.press(*names)
        try:
            self.sleep(hold)
        finally:
            self.release(*names)

    def tap_record(self, record: int, hold: float = HOLD) -> None:
        """The button (and LT for 6-11) of a controller record."""
        self.combo(*record_buttons(record), hold=hold)

    def stick(self, side: str, x: float, y: float) -> None:
        """Put stick `side` at screen direction (x right, y down), each in -1..1; magnitude over 1 is cut to 1.
        (0, 0) centres it. The game takes a stick past 40% as input (and as a reason to flip to controller)."""
        if side not in STICKS:
            raise ValueError(f'no stick named {side!r}')
        length = (x * x + y * y) ** 0.5
        if length > 1:
            x, y = x / length, y / length
        if (x, y) != (0, 0):
            self.settle()  # centring never waits
        axis_x, axis_y = STICKS[side]
        self.event(EV_ABS, axis_x, round(x * STICK_MOST))
        self.event(EV_ABS, axis_y, round(y * STICK_MOST))
        self.report()
        self.sticks[side] = (x, y)

    def hold_stick(self, side: str, x: float, y: float, seconds: float) -> None:
        """The stick at (x, y) for `seconds`, then centred (centring sends the game's stop)."""
        self.stick(side, x, y)
        try:
            self.sleep(seconds)
        finally:
            self.stick(side, 0.0, 0.0)

    def held(self) -> bool:
        """Whether anything is off rest: a held input blocks the game's way back to mouse mode."""
        return bool(self.down) or any(position != (0.0, 0.0) for position in self.sticks.values())

    def neutral(self) -> None:
        """Everything let go and both sticks centred."""
        for name in sorted(self.down):
            self._set(name, False)
        for side in STICKS:
            if self.sticks[side] != (0.0, 0.0):
                axis_x, axis_y = STICKS[side]
                self.event(EV_ABS, axis_x, 0)
                self.event(EV_ABS, axis_y, 0)
                self.sticks[side] = (0.0, 0.0)
        self.report()

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.neutral()
        try:
            fcntl.ioctl(self.file, UI_DEV_DESTROY)
        finally:
            os.close(self.file)


class PadKeys:
    """The experiment's hotkeys: a press taps one pad button. The device is made at the first press, so
    that a session with no press of them is played with no pad plugged in, and kept from then on.
    `pressed_at` is the clock time of the last tap (tracking/input_mode.py times flips from it)."""

    def __init__(self, make=Pad, clock=time.monotonic) -> None:
        self.make = make
        self.clock = clock
        self.pad: Pad | None = None
        self.refused: str | None = None
        self.pressed_at: float | None = None

    def start(self) -> None:
        """Say at the service's start whether the pad can be made (the experiment's first question)."""
        why = problem()
        if why is None:
            LOG.info('Gamepad experiment: a virtual pad can be made; it appears at the first pad hotkey')
        else:
            LOG.warning('Gamepad experiment: no virtual pad: %s', why)

    def device(self) -> Pad | None:
        """The pad, made at its first need and kept: a hotkey's tap, or the macros' first act in controller mode
        (macros/pad.py: one device for the session, the hotkey's and the macros'). None when it cannot be made."""
        if self.pad is None:
            why = problem()
            if why is not None:
                LOG.warning('Gamepad: %s', why)
                return None
            try:
                self.pad = self.make()
            except OSError as exc:
                LOG.warning('Gamepad: the pad was not made: %s', exc)
                return None
            LOG.info('Gamepad: the pad is plugged in (%s)', NAME.decode())
        return self.pad

    def request(self, button: str, requested: float, now: float) -> bool:
        if not 0 <= now - requested <= 1 or button not in names():
            return False
        if self.device() is None:
            return False
        assert self.pad is not None
        began = self.clock()
        self.pad.tap(button)
        # The client asks for the flip on the button's down, after the first tap's settling wait.
        self.pressed_at = getattr(self.pad, 'pressed_at', None) or began
        LOG.info('Gamepad experiment: %s tapped (%.0f ms)', button.upper(), 1000 * (self.clock() - began))
        return True

    def close(self) -> None:
        if self.pad is not None:
            self.pad.close()
            self.pad = None
