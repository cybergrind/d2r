"""Uber Diablo (Diablo Clone) progress on the HUD: which region he is close to walking in (user, 2026-10-11).

Each region and mode counts Stones of Jordan sold in six steps; at the sixth Diablo walks. `serve` polls diablo2.io's
tracker every `poll_seconds` and shows the player's mode's regions at `minimum_progress` or more in the Traderie slot.

The tracker bans an address that asks a few times a minute (2026-10-11: four requests in a minute, a ban that
outlasted restarts), so the last answer and the next request time live in `cache`; a failure waits for Retry-After,
else `poll_seconds` doubled per failure up to `backoff_seconds`.

API (diablo2.io forum t906872, read 2026-10-11): `ver` 1 = LoD, 2 = RotW; `ladder` 2 = Non-Ladder; `hc` 2 = Softcore;
requests ≥ 60 s apart; the card must show "Data courtesy of diablo2.io". d2emu.com needs a granted token: not asked.
An answer without the player's rows is a failed check.
"""

import email.utils
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
from inventory_tracking.reports import publish


PRODUCER = 'dclone'
REGIONS = {'1': 'Americas', '2': 'Europe', '3': 'Asia'}
STEPS = 6
CREDIT = 'Data courtesy of diablo2.io'  # the API's condition of use
# The same browser user agent as pricing/tools/fetch.sh: diablo2.io answers it.
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'


class Refused(OSError):
    """A request the tracker did not answer, with the wait it asked for (Retry-After), if any."""

    def __init__(self, reason: str, retry_after: float | None = None):
        super().__init__(reason)
        self.retry_after = retry_after


def retry_after(value: str | None, wall: float) -> float | None:
    """Seconds to wait from a Retry-After header: a number of seconds or an HTTP date."""
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        pass
    try:
        return max(email.utils.parsedate_to_datetime(value).timestamp() - wall, 0.0)
    except TypeError, ValueError:
        return None


def fetch(config=DCLONE) -> list:
    query = urllib.parse.urlencode({'ver': config.version, 'ladder': config.ladder, 'hc': config.hardcore})
    request = urllib.request.Request(f'{config.url}?{query}', headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            return json.loads(answer.read())
    except urllib.error.HTTPError as error:
        wait = retry_after(error.headers.get('Retry-After'), time.time())
        raise Refused(f'HTTP {error.code} {error.reason}', wait) from error


def stored(path: Path) -> dict:
    """The cache file: 'answer' with 'fetched_at', and 'retry_at' (epoch seconds), each when known."""
    try:
        record = json.loads(path.read_text())
    except OSError, ValueError:
        return {}
    return record if isinstance(record, dict) else {}


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

    def lines(self, now: float) -> list[StyledLine]:
        """`now` and the `now` of `feed` in epoch seconds, as the tracker's own times are."""
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
        lines += [StyledLine(f'{region}: changed {ago(now - changed)}', Tone.METADATA) for _, region, changed in close]
        lines.append(StyledLine(CREDIT, Tone.METADATA))
        waited = now - self.checked_at
        if waited > self.config.stale_seconds:
            lines.append(
                StyledLine(f'not checked for {waited / 60:.0f} min: {self.error or "no answer"}', Tone.WARNING)
            )
        return lines


def dclone_widgets(lines) -> list[Widget]:
    return [Widget('dclone', 'text', 'traderie', card_payload(lines))] if lines else []


def follow(state: Progress, publish_card, stop, *, ask=fetch, wall=time.time, interval=LEASE_SECONDS / 3):
    """Show the stored answer, ask the tracker when a request is due and publish the card every
    `interval`, until `stop` is set."""
    config = state.config
    record = stored(config.cache)
    if 'answer' in record:
        state.feed(record['answer'], float(record.get('fetched_at', 0.0)))
    due = max(float(record.get('fetched_at', 0.0)) + config.poll_seconds, float(record.get('retry_at', 0.0)))
    failures = 0
    while not stop.is_set():
        now = wall()
        if now >= due:
            try:
                answer = ask(config)
                state.feed(answer, now)
            except (OSError, ValueError) as error:  # no network, HTTP 429, a page that is not JSON
                failures += 1
                asked = getattr(error, 'retry_after', None)
                wait = min(config.poll_seconds * 2**failures, config.backoff_seconds) if asked is None else asked
                due = now + max(wait, config.poll_seconds)
                state.fail(f'{error or type(error).__name__}; next request in {(due - now) / 60:.0f} min')
                record = record | {'retry_at': due}
            else:
                # An answer without the player's rows is kept out of the file: `feed` called it a failure.
                failures, due = 0, now + config.poll_seconds
                if state.error is None:
                    record = {'answer': answer, 'fetched_at': now}
            try:
                config.cache.parent.mkdir(parents=True, exist_ok=True)
                publish(config.cache, record)
            except OSError as error:
                LOG.warning('Uber Diablo progress could not be stored: %s', error)
        publish_card(dclone_widgets(state.lines(now)))
        stop.wait(interval)
    publish_card([])


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
