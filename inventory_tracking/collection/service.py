"""Win+S handling inside the Alt+D worker process.

The compositor binding sends `collect <monotonic>` (Win+S: every owned container,
the mercenary's equipment and the character sheet) to the appraisal socket; the
stash watcher (watch.py) requests the same collection whenever the stash panel closes;
`equipped <monotonic>` (`request --equipped`, no binding) records only what the
character and the mercenary wear. The memory pass runs under the same capture lock
Alt+D uses, so the two never read at once; decoding and the database write
continue on a background thread and the result is announced through the same
desktop notification path. Both requests write the same database: an equipment
capture is authoritative for the `equipped` and `mercenary` containers only, so
inventory and stash placements from the last Win+S stay open.
"""

import math
import threading
import time
from pathlib import Path
from typing import Any

from inventory_tracking.collection.capture import Scope, build_sightings, collect_inventory
from inventory_tracking.collection.export import DEFAULT_HTML, export_html
from inventory_tracking.collection.models import CaptureRun
from inventory_tracking.collection.store import CollectionStore
from inventory_tracking.common import LOG, timestamp
from inventory_tracking.reports import create_run, publish


DEFAULT_OUTPUT = Path('inventory_tracking/runs/collection')
REQUEST_PREFIX = 'collect '
EQUIPMENT_PREFIX = 'equipped '


def record_collection(
    directory: Path, report: dict[str, Any], record: dict[str, Any], database: Path, html: Path | None = None
):
    """Decode a live record, store it, regenerate the page, fill the run report; shared by CLI and hotkey."""
    publish(directory / 'capture.json', record)
    build = build_sightings(record, run_id=report['run_id'], captured_at=timestamp())
    run = CaptureRun(
        id=report['run_id'],
        character=build.character,
        containers=build.containers,
        started_at=report['started_at'],
        status='complete',
        item_count=len(build.sightings),
    )
    with CollectionStore(database) as store:
        summary = store.record_capture(run, build.sightings, build.spaces, build.character_stats)
        if html is not None:
            export_html(store, html)
    report.update(
        state='complete',
        finished_at=timestamp(),
        scope=build.scope,
        character=build.character.model_dump(),
        character_stats=None if build.character_stats is None else build.character_stats.sheet(),
        tabs={str(k): v for k, v in build.tabs.items()},
        containers=[list(c) for c in build.containers],
        summary=summary.model_dump(),
        issues=build.issues,
        timing=record['timing'],
        location=record['location'],
        database=str(database),
        html=None if html is None else str(html),
    )
    return build, summary


def describe(build, summary) -> tuple[str, str]:
    """Notification title and body for one completed collection."""
    if build.scope == 'equipment':
        worn = sum(1 for s in build.sightings if s.location.container == 'equipped')
        merc = sum(1 for s in build.sightings if s.location.container == 'mercenary')
        title = f'{build.character.name}: {summary.text("equipped items")}'
        body = f'{worn} on the character, {merc} on the mercenary'
    else:
        title = f'{build.character.name}: {summary}'
        body = f'{len(build.tabs)} shared tabs' if build.tabs else 'no shared tabs'
    if build.issues:
        body += f'; {len(build.issues)} issues'
    stats = getattr(build, 'character_stats', None)
    return title, f'{body}\n{stats.summary}' if stats is not None else body


class Collector:
    """Serializes collection requests; one collection at a time, fresh requests only."""

    def __init__(
        self,
        source,
        database: Path,
        output: Path,
        executor,
        *,
        html: Path | None = DEFAULT_HTML,
        capture_lock: threading.Lock,
        focused,
        notify,
        clock=time.monotonic,
        collect=collect_inventory,
        record=record_collection,
    ):
        self.source, self.database, self.output, self.executor = source, database, output, executor
        self.html = html
        self.capture_lock, self.focused, self.notify, self.clock = capture_lock, focused, notify, clock
        self.collect, self.record = collect, record
        self.lock = threading.Lock()
        self.busy = False
        self.last_request = -math.inf
        self.future = None

    def request(self, requested_at: float, now: float, scope: Scope = 'all', *, trigger: str = 'hotkey') -> bool:
        """Start one collection; `trigger` names the source (hotkey or stash-closed watcher).

        Watcher-triggered failures are logged, not announced: the stash flag also drops
        when the game ends, and that must not raise a notification.
        """
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1 or now - self.last_request < 1:
            return False
        with self.lock:
            if self.busy:
                return False
            self.busy = True
            self.last_request = now
        directory, created = create_run(self.output)
        report: dict[str, Any] = dict(created, scope=scope, trigger=trigger)
        quiet = trigger != 'hotkey'
        try:
            with self.capture_lock:
                self.source.ensure_connected()
                if not self.focused(self.source.images):
                    raise ValueError('D2R is not focused')
                record = self.collect(self.source.pid, self.source.images, self.source.capture, scope=scope)
        except Exception as exc:
            self._finish(directory, report, error=str(exc), quiet=quiet)
            return False
        self.future = self.executor.submit(self._complete, directory, report, record, quiet)
        return True

    def _complete(self, directory, report, record, quiet=False):
        try:
            build, summary = self.record(directory, report, record, self.database, self.html)
        except Exception as exc:
            self._finish(directory, report, error=str(exc), quiet=quiet)
            return
        title, body = describe(build, summary)
        LOG.info('Collection %s: %s (%s)', report['run_id'], title, body)
        for issue in build.issues:
            LOG.warning('Collection issue: %s', issue)
        page = f'\nPage: {self.html}' if self.html is not None else ''
        self._finish(directory, report, title=title, body=f'{body}{page}\nReport: {directory}')

    def _finish(self, directory, report, *, error=None, title=None, body='', quiet=False):
        if error is not None:
            report.update(state='failed', error=error, finished_at=timestamp())
            LOG.warning('Collection rejected: %s', error)
            title, body = 'Collection unavailable', error
        publish(directory / 'report.json', report)
        with self.lock:
            self.busy = False
        if not (quiet and error is not None):
            self.notify(title, body)
