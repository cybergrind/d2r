"""Host probes for the macro plan (plan.md, research gates). Run on the host, next to the game.

`record` sends nothing: once a second it saves the game image's writable memory and the panel
flags while the player does one manual cycle (town, menu, Save and Exit, lobby, next game), so
the game name, the lobby/in-game flags and the skill slots can be found afterwards.

`pointer` sends input: Escape, then a synthetic pointer move and click on "Return to Game",
and reports whether the quit menu closed (gate R1: do XTest pointer events reach the game).

Both write `report.json` into a new run directory and point `latest-<probe>.json` at it.
"""

import argparse
import math
import os
import random
import time
import zlib
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.config import INPUT
from inventory_tracking.input.focus import FocusTracker, owns_process
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.macros.actuator import eased_path
from inventory_tracking.models import SessionIdentity
from inventory_tracking.native.image_probe import inspect_images
from inventory_tracking.native.layout import PANEL_FLAGS, UI_PANELS_RVA, UI_PANELS_SIZE
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.session import inspect_game, select_game_process
from inventory_tracking.reports import create_run, publish


OUTPUT = Path('inventory_tracking/runs/macro')
# "Return to Game" in the quit menu, as fractions of the game window (screenshot 2026-10-06).
RETURN_TO_GAME = (0.5, 0.509)
QUIT_MENU = PANEL_FLAGS['quit_menu']
# Flags that mean something is open. The array also holds bytes that are set with nothing open
# (Show Items, belt rows and unnamed ones: first pointer run, 2026-10-06), so "all zero" is wrong.
OPEN_PANELS = tuple(offset for name, offset in PANEL_FLAGS.items() if name != 'belt_rows')


def anything_open(panels: bytes) -> bool:
    return any(panels[offset] for offset in OPEN_PANELS)


def writable_regions(mappings, base: int, size: int) -> list[tuple[int, int]]:
    """(start, length) of the writable parts of the image at `base`: its data, not its code."""
    end = base + size
    return [
        (max(m['start'], base), min(m['end'], end) - max(m['start'], base))
        for m in mappings
        if m['start'] < end and m['end'] > base and 'w' in m['permissions'] and m['permissions'].startswith('r')
    ]


def read_regions(fd: int, regions) -> bytes:
    """The regions back to back; an unreadable megabyte stays zero so offsets never shift."""
    parts = []
    for start, length in regions:
        for offset in range(0, length, 0x100000):
            count = min(0x100000, length - offset)
            try:
                data = os.pread(fd, count, start + offset)
            except OSError:
                data = b''
            parts.append(data.ljust(count, b'\0'))
    return b''.join(parts)


def attach(pid) -> tuple[int, dict[str, Any]]:
    pid = select_game_process(pid)
    game = inspect_game(pid)
    images = inspect_images(pid, game)
    if images.get('status') != 'candidate':
        raise RuntimeError(f'Game image not found: {images.get("error") or images.get("status")}')
    return pid, images


def image_size(images) -> int:
    return next(image['pe']['image_size'] for image in images['images'] if image['base'] == images['candidate_base'])


def finish(directory: Path, report: dict[str, Any], name: str) -> int:
    report['finished_at'] = timestamp()
    publish(directory / 'report.json', report)
    publish(OUTPUT / f'latest-{name}.json', report | {'directory': str(directory)})
    LOG.info('%s probe %s: %s', name, report['state'], directory)
    return 0 if report['state'] == 'complete' else 1


def record(args) -> int:
    directory, created = create_run(args.output)
    report: dict[str, Any] = dict(created)
    with log_to_file(directory / 'probe.log'):
        try:
            pid, images = attach(args.pid)
            base = images['candidate_base']
            regions = writable_regions(process_mappings(pid), base, image_size(images))
            report.update(
                probe='record',
                game_name=args.game_name,
                base=base,
                regions=[[start - base, length] for start, length in regions],
                panels_rva=UI_PANELS_RVA,
                samples=[],
            )
            LOG.info(
                'Recording %.1f MB of image data every %ss for %ss; Ctrl+C stops early',
                sum(length for _, length in regions) / 1e6,
                args.interval,
                args.duration,
            )
            token = identity(pid)
            fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
            try:
                started = time.monotonic()
                while time.monotonic() - started < args.duration and identity(pid) == token:
                    at = time.monotonic() - started
                    data = read_regions(fd, regions)
                    panels = data_at(data, regions, base + UI_PANELS_RVA, UI_PANELS_SIZE)
                    name = f'{len(report["samples"]):04d}.z'
                    (directory / name).write_bytes(zlib.compress(data, 1))
                    report['samples'].append({'at': round(at, 3), 'file': name, 'panels': panels.hex()})
                    publish(directory / 'report.json', report)
                    time.sleep(max(0.0, args.interval - (time.monotonic() - started - at)))
            except KeyboardInterrupt:
                LOG.info('Stopped by Ctrl+C')
            finally:
                os.close(fd)
            report['state'] = 'complete' if report['samples'] else 'failed'
        except Exception as exc:
            LOG.exception('Record probe failed')
            report.update(state='failed', error=str(exc))
        return finish(directory, report, 'record')


def data_at(data: bytes, regions, address: int, size: int) -> bytes:
    """`size` bytes at `address` out of a `read_regions` result; empty when not covered."""
    offset = 0
    for start, length in regions:
        if start <= address and address + size <= start + length:
            return data[offset + address - start : offset + address - start + size]
        offset += length
    return b''


def read_panels(fd: int, base: int) -> bytes:
    return os.pread(fd, UI_PANELS_SIZE, base + UI_PANELS_RVA)


def wait_for(predicate, timeout: float, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def tap(keys, code: int, rng) -> None:
    keys.press(code)
    keys.sync()
    time.sleep(rng.uniform(0.045, 0.1))
    keys.release(code)
    keys.sync()


def pointer(args) -> int:
    directory, created = create_run(args.output)
    report: dict[str, Any] = dict(created)
    rng = random.Random()
    with log_to_file(directory / 'probe.log'):
        focus = FocusTracker(INPUT)
        try:
            pid, images = attach(args.pid)
            base = images['candidate_base']
            session = SessionIdentity(pid, identity(pid)['start_ticks'], 0)
            report.update(probe='pointer', target=list(RETURN_TO_GAME), stages=[])
            focus.wait_ready(timeout=1)
            fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
            try:
                with X11Keyboard().connect() as keys:
                    if keys is None:
                        raise RuntimeError('No X display')

                    def stage(name, **extra):
                        panels = read_panels(fd, base)
                        report['stages'].append(
                            {'stage': name, 'panels': panels.hex(), 'quit_menu': panels[QUIT_MENU], **extra}
                        )
                        publish(directory / 'report.json', report)
                        return panels

                    def ready():
                        return (
                            focus(session)
                            and owns_process(keys.focused_window_pid(), session)
                            and not keys.any_key_held()
                        )

                    LOG.info('Switch to the game now (in town, nothing open); waiting up to %ss', args.wait)
                    if not wait_for(ready, args.wait, 0.1):
                        raise RuntimeError('The game did not get the focus with all keys released')
                    time.sleep(rng.uniform(0.8, 1.2))
                    before = stage('start')
                    if anything_open(before):
                        raise RuntimeError('A panel or menu is open; close everything and run again')
                    codes = keys.keycodes([b'Escape'])
                    if not codes or not ready():
                        raise RuntimeError('Escape has no keycode, or the game lost the focus')
                    tap(keys, codes[0], rng)
                    opened = wait_for(lambda: read_panels(fd, base)[QUIT_MENU] == 1, 2)
                    stage('after escape', menu_flag_seen=opened)
                    rect = keys.focused_window_rect()
                    start = keys.pointer()
                    if rect is None or start is None or not ready():
                        raise RuntimeError('No window geometry or pointer position, or the game lost the focus')
                    goal = (
                        rect[0] + round(rect[2] * RETURN_TO_GAME[0]) + rng.randint(-12, 12),
                        rect[1] + round(rect[3] * RETURN_TO_GAME[1]) + rng.randint(-5, 5),
                    )
                    for x, y in eased_path(start, goal, 14, rng):
                        keys.move_pointer(x, y)
                        keys.sync()
                        time.sleep(rng.uniform(0.008, 0.02))
                    time.sleep(rng.uniform(0.15, 0.3))
                    arrived = keys.pointer()
                    stage('after move', window=list(rect), pointer_before=list(start), goal=list(goal), pointer=arrived)
                    keys.button(1, True)
                    keys.sync()
                    time.sleep(rng.uniform(0.05, 0.1))
                    keys.button(1, False)
                    keys.sync()
                    closed = wait_for(lambda: read_panels(fd, base) == before, 2)
                    after = stage('after click', closed=closed)
                    if opened and after[QUIT_MENU] == 1 and ready():
                        tap(keys, codes[0], rng)  # leave the game as it was found
                        wait_for(lambda: read_panels(fd, base) == before, 2)
                        stage('after closing escape')
                    report['result'] = (
                        'the click reached the game'
                        if opened and closed
                        else 'the quit menu flag was never seen; look at the stages'
                        if not opened
                        else 'the menu stayed open: the click did not reach the button'
                    )
                    report['state'] = 'complete'
            finally:
                os.close(fd)
        except Exception as exc:
            LOG.exception('Pointer probe failed')
            report.update(state='failed', error=str(exc))
        finally:
            focus.close()
        if 'result' in report:
            LOG.info('Result: %s', report['result'])
        return finish(directory, report, 'pointer')


def positive(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pid', type=int, help='pin one D2R process')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    commands = parser.add_subparsers(dest='command', required=True)
    recorder = commands.add_parser('record', help='save image data once a second; sends no input')
    recorder.add_argument('--game-name', required=True, help='name of the game you are in now, e.g. cyber40')
    recorder.add_argument('--duration', type=positive, default=120)
    recorder.add_argument('--interval', type=positive, default=1)
    pointing = commands.add_parser('pointer', help='Escape, then move and click on "Return to Game"')
    pointing.add_argument('--wait', type=positive, default=15, help='seconds to wait for the game to get the focus')
    args = parser.parse_args(argv)
    configure_logging()
    args.output.mkdir(parents=True, exist_ok=True)
    return record(args) if args.command == 'record' else pointer(args)


if __name__ == '__main__':
    raise SystemExit(main())
