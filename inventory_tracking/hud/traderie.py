"""Traderie notifications on the HUD, shown with or without the game (HUD.desktop_slots).

`serve` runs pricing/tools/traderie_notifications.mjs --watch, which reads the player's
notifications through their own browser and prints one JSON line per check. The unread ones are a
text card in the 'traderie' slot until they are read on Traderie. The watch has its own thread, so
the scene lease is renewed while `serve` waits for the game or a loop step runs long.
"""

import json
import os
import select
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import TRADERIE
from inventory_tracking.hud.payloads import card_payload
from inventory_tracking.hud.process import hud_process
from inventory_tracking.hud.scene import DEFAULT_SCENE, LEASE_SECONDS, Widget, publish_layer
from inventory_tracking.presentation import StyledLine, Tone


SCRIPT = Path(__file__).resolve().parents[2] / 'pricing/tools/traderie_notifications.mjs'
PRODUCER = 'traderie'


def unread(answer) -> list[dict]:
    """The unread notifications of one reader line, newest first."""
    found = [n for n in answer.get('notifications', []) if isinstance(n, dict) and not n.get('read')]
    return sorted(found, key=lambda n: str(n.get('created_at', '')), reverse=True)


def notification_lines(notifications, *, limit=TRADERIE.max_lines) -> list[StyledLine]:
    """A heading with the count, then the newest messages; the rest as "+N more"."""
    if not notifications:
        return []
    lines = [StyledLine(f'Traderie: {len(notifications)} new', Tone.VALUABLE)]
    lines += [
        StyledLine(' '.join(str(n.get('message') or n.get('title') or '?').split())) for n in notifications[:limit]
    ]
    if len(notifications) > limit:
        lines.append(StyledLine(f'+{len(notifications) - limit} more', Tone.METADATA))
    return lines


def traderie_widgets(lines) -> list[Widget]:
    return [Widget('traderie', 'text', 'traderie', card_payload(lines))] if lines else []


class Notifications:
    """The reader's latest answer. Unread notifications stay until Traderie says they are read; when
    no check has succeeded for `stale_seconds` (browser closed, logged out) the card says so."""

    def __init__(self, config=TRADERIE):
        self.config = config
        self.unread: list[dict] = []
        self.checked_at: float | None = None
        self.error: str | None = None

    def feed(self, text: str, now: float) -> None:
        try:
            answer = json.loads(text)
            if not isinstance(answer, dict):
                raise ValueError('not an object')
        except ValueError:
            LOG.warning('Traderie reader printed an unreadable line: %.200s', text)
            return
        error = answer.get('error')
        if error != self.error:
            if error:
                LOG.warning('Traderie notifications unavailable: %s', error)
            else:
                LOG.info('Traderie notifications are being read')
            self.error = error
        if error:
            return  # the last known unread ones stay (user, 2026-10-09: shown until read)
        fresh = unread(answer)
        if {n.get('id') for n in fresh} - {n.get('id') for n in self.unread}:
            LOG.info('Traderie: %s unread notification(s)', len(fresh))
        self.unread, self.checked_at = fresh, now

    def lines(self, now: float) -> list[StyledLine]:
        if self.checked_at is None:
            return []
        lines = notification_lines(self.unread, limit=self.config.max_lines)
        waited = now - self.checked_at
        if lines and waited > self.config.stale_seconds:
            lines.append(
                StyledLine(f'not checked for {waited / 60:.0f} min: {self.error or "no answer"}', Tone.WARNING)
            )
        return lines


def follow(stream, state: Notifications, publish, stop, *, clock=time.monotonic, interval=LEASE_SECONDS / 3):
    """Feed the reader's lines to `state` and publish its card every `interval`, until `stop` is set
    or the reader's output ends."""
    descriptor, buffer = stream.fileno(), b''
    while not stop.is_set():
        ready, _, _ = select.select([descriptor], [], [], interval)
        if ready:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                if stop.is_set():
                    break
                LOG.warning('Traderie reader stopped; no notifications will be shown')
                break
            *lines, buffer = (buffer + chunk).split(b'\n')
            for line in lines:
                if line.strip():
                    state.feed(line.decode('utf-8', 'replace'), clock())
        publish(traderie_widgets(state.lines(clock())))
    publish([])


@contextmanager
def traderie_watch(scene_dir: Path, enabled: bool, log: Path, config=TRADERIE):
    """Run the reader and its publishing thread for the producer's lifetime."""
    node = shutil.which('node') if enabled else None
    if node is None:
        if enabled:
            LOG.warning('Traderie notifications are off: node is not installed')
        yield
        return
    command = [node, str(SCRIPT), '--watch', '--interval', f'{config.poll_seconds:g}', '--port', str(config.port)]
    with log.open('a') as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        stream = process.stdout
        assert stream is not None
        stop = threading.Event()
        thread = threading.Thread(
            target=follow,
            args=(
                stream,
                Notifications(config),
                lambda widgets: publish_layer(scene_dir, PRODUCER, widgets),
                stop,
            ),
            name='traderie',
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stop.set()
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            thread.join(timeout=3)
            stream.close()


def preview(scene_dir: Path, seconds: float, log: Path) -> None:
    """Show a sample card for `seconds`, as its own producer, starting a canvas if none runs."""
    sample = [
        {'message': 'sample_buyer made an offer for Grand charm', 'created_at': '3'},
        {'message': 'You got a new message from sample_buyer', 'created_at': '2'},
        {'message': 'other_buyer made an offer for Buriza-Do Kyanon', 'created_at': '1'},
        {'message': "other_buyer cancelled their offer for Gheed's Fortune", 'created_at': '0'},
    ]
    card = card_payload(notification_lines(unread({'notifications': sample})))
    widgets = [Widget('traderie-preview', 'text', 'traderie', card)]
    with hud_process(scene_dir, True, log):
        try:
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                publish_layer(scene_dir, 'traderie-preview', widgets)
                time.sleep(LEASE_SECONDS / 3)
        finally:
            publish_layer(scene_dir, 'traderie-preview', [])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Show a sample Traderie notifications card on the HUD.')
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--scene', type=Path, default=DEFAULT_SCENE)
    arguments = parser.parse_args()
    preview(arguments.scene, arguments.seconds, arguments.scene / 'preview.log')
