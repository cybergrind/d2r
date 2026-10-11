"""Uber Diablo (Diablo Clone) progress on the HUD: which region he is close to walking in (user, 2026-10-11).

Every region and game mode has its own count of Stones of Jordan sold, in six steps; at the sixth
Diablo walks in that region's games. `serve` asks diablo2.io's tracker (fed by d2emu.com) every
`poll_seconds` and shows the regions of the player's mode at `minimum_progress` or more as a text card
in the Traderie slot, with or without the game. The tracker bans an address that asks a few times a
minute (HTTP 429, Cloudflare 1015: four requests in a minute on 2026-10-11), so the poll is slow, and
a failed check keeps the last answer.

Rows are told apart by `ver`: the page lists 1 as LoD and 2 as RotW, and the answer without a `ver`
parameter held only `ver` 1 rows, equal to the page's LoD table. UNCONFIRMED: that the `ver=2` parameter
returns the RotW rows (the ban came first). Rows of another version or mode are never shown, so a
wrong parameter gives a card that says nothing was found, not another economy's progress.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import DCLONE
from inventory_tracking.hud.payloads import card_payload
from inventory_tracking.hud.scene import LEASE_SECONDS, Widget, publish_layer
from inventory_tracking.presentation import StyledLine, Tone


PRODUCER = 'dclone'
REGIONS = {'1': 'Americas', '2': 'Europe', '3': 'Asia'}
STEPS = 6
# The same browser user agent as pricing/tools/fetch.sh: diablo2.io answers it.
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'


def fetch(config=DCLONE) -> list:
    query = urllib.parse.urlencode({'ver': config.version, 'ladder': config.ladder, 'hc': config.hardcore})
    request = urllib.request.Request(f'{config.url}?{query}', headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as answer:
        return json.loads(answer.read())


def progress(answer, config=DCLONE) -> dict[str, tuple[int, int]]:
    """Region name -> (step, when it last changed as epoch seconds), for the player's version and mode."""
    mode = {'ver': config.version, 'ladder': config.ladder, 'hc': config.hardcore}
    found = {}
    for row in answer if isinstance(answer, list) else []:
        if not isinstance(row, dict) or any(str(row.get(key)) != value for key, value in mode.items()):
            continue
        try:
            found[REGIONS[str(row['region'])]] = (int(row['progress']), int(row['timestamped']))
        except KeyError, ValueError:
            continue
    return found


def ago(seconds: float) -> str:
    if seconds < 3600:
        return f'{max(seconds, 0) / 60:.0f} min ago'
    return f'{seconds / 3600:.0f} h ago' if seconds < 2 * 86400 else f'{seconds / 86400:.0f} d ago'


class Progress:
    """The tracker's latest answer. The card lists the regions at `minimum_progress` or more, the
    nearest to the walk first; when no check has succeeded for `stale_seconds` it says so."""

    def __init__(self, config=DCLONE):
        self.config = config
        self.regions: dict[str, tuple[int, int]] = {}
        self.checked_at: float | None = None
        self.error: str | None = None

    def feed(self, answer, now: float) -> None:
        found = progress(answer, self.config)
        if not found:
            self.fail('no row of this version and mode in the answer')
            return
        if self.error:
            LOG.info('Uber Diablo progress is being read')
        for region, (step, _) in sorted(found.items()):
            if step != self.regions.get(region, (None, 0))[0]:
                LOG.info('Uber Diablo: %s is at %d/%d', region, step, STEPS)
        self.regions, self.checked_at, self.error = found, now, None

    def fail(self, error: str) -> None:
        if error != self.error:
            LOG.warning('Uber Diablo progress unavailable: %s', error)
        self.error = error

    def lines(self, now: float, wall: float) -> list[StyledLine]:
        """`now` on the clock of `feed`; `wall` in epoch seconds, for the age of a region's last change."""
        close = sorted(
            ((step, region, changed) for region, (step, changed) in self.regions.items()),
            key=lambda entry: (-entry[0], entry[1]),
        )
        close = [entry for entry in close if entry[0] >= self.config.minimum_progress]
        if self.checked_at is None or not close:
            return []
        lines = [
            StyledLine(
                f'Uber Diablo {step}/{STEPS} {region}' + (' - walking' if step >= STEPS else ''),
                Tone.VALUABLE if step >= STEPS - 1 else Tone.DEMAND,
            )
            for step, region, _ in close
        ]
        lines += [StyledLine(f'{region}: changed {ago(wall - changed)}', Tone.METADATA) for _, region, changed in close]
        waited = now - self.checked_at
        if waited > self.config.stale_seconds:
            lines.append(
                StyledLine(f'not checked for {waited / 60:.0f} min: {self.error or "no answer"}', Tone.WARNING)
            )
        return lines


def dclone_widgets(lines) -> list[Widget]:
    return [Widget('dclone', 'text', 'traderie', card_payload(lines))] if lines else []


def follow(
    state: Progress, publish, stop, *, ask=fetch, clock=time.monotonic, wall=time.time, interval=LEASE_SECONDS / 3
):
    """Ask the tracker every `poll_seconds` and publish the card every `interval`, until `stop` is set."""
    due = clock()
    while not stop.is_set():
        if clock() >= due:
            due = clock() + state.config.poll_seconds
            try:
                state.feed(ask(state.config), clock())
            except (OSError, ValueError) as error:  # no network, HTTP 429, a page that is not JSON
                state.fail(str(error) or type(error).__name__)
        publish(dclone_widgets(state.lines(clock(), wall())))
        stop.wait(interval)
    publish([])


@contextmanager
def dclone_watch(scene_dir: Path, enabled: bool, config=DCLONE):
    """Run the tracker's polling thread for the producer's lifetime."""
    if not enabled:
        yield
        return
    stop = threading.Event()
    thread = threading.Thread(
        target=follow,
        args=(Progress(config), lambda widgets: publish_layer(scene_dir, PRODUCER, widgets), stop),
        name='dclone',
        daemon=True,
    )
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=3)
