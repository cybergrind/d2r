"""Win+D shop scans plus an automatic stock watcher keyed on the first gear item.

Watcher rules (2026-09-26): poll loaded vendor stock and remember its first
weapons/armor item; never rescan while that item is unchanged (closing and
reopening Trade keeps the stock, and the result is shown only once per stock);
rescan when it changes (leaving and returning to town refreshes stock); a manual
Win+D always scans and shows. Results with targets stay 10 s, everything else 5 s,
and any result disappears early when its stock leaves memory.
"""

import math
import threading
import time
from typing import Any

from inventory_tracking.common import LOG, timestamp
from inventory_tracking.presentation import StyledLine, Tone
from inventory_tracking.reports import publish
from inventory_tracking.shop.capture import capture_sentinel, capture_shop, decode_stock
from inventory_tracking.shop.rules import match_item, skill_targets


REQUEST_PREFIX = 'shop '
AUTO_ATTEMPTS = 3  # failed automatic scans per stock key before waiting for a change or Win+D
AWAY_BACKOFF = 5  # poll interval multiplier outside town
HIT_SECONDS = 10  # OSD lease for a result with shopping targets
QUIET_SECONDS = 5  # OSD lease for no-target results, status and failures


def assess(record):
    observations, issues = decode_stock(record)
    hits = []
    for observation in observations:
        reasons = match_item(observation)
        if reasons:
            hits.append(
                {
                    'name': observation['item']['name'],
                    'vendor': observation['vendor'],
                    'position': observation['source']['position'],
                    'page': observation['source']['container']['page'],
                    'reasons': reasons,
                }
            )
        if observation.get('unresolved_stats'):
            payloads = ', '.join(
                f'{stat["id"]}:{stat["layer"]} raw={stat["raw"]}' for stat in observation['unresolved_stats']
            )
            issues.append(
                f'{observation["vendor"]} {observation["item"]["name"]} '
                f'item {observation["source"]["unit_id"]}: unresolved stats {payloads}'
            )
    return {
        'state': 'complete' if not issues else 'partial',
        'count': len(observations),
        'stock_count': record['stock_count'],
        'hits': hits,
        'issues': issues,
        'vendors': sorted({o['vendor'] for o in observations}),
        'timing': record['timing'],
        'sentinel': record.get('sentinel'),
    }


def result_lines(result):
    if result['state'] == 'failed':
        return [StyledLine('Shop check unavailable', Tone.WARNING), StyledLine(result['error'])]
    hits, count = result['hits'], result['count']
    if not result['stock_count']:
        return [
            StyledLine('Shop stock is not loaded', Tone.WARNING),
            StyledLine('Open Trade once, then press Win+D. No items were checked.'),
        ]
    vendors = ', '.join(result['vendors'])
    if hits:
        lines = [StyledLine(f'Shop: {len(hits)} targets found — {vendors} ({count} checked)', Tone.VALUABLE)]
        for hit in hits[:6]:
            x, y = hit['position']
            position = f'({x + 1}, {y + 1})' if isinstance(x, int) and isinstance(y, int) else 'unknown cell'
            lines.append(StyledLine(f'{hit["vendor"]}: {hit["name"]} — tab {hit["page"] + 1}, {position}', Tone.MAGIC))
            lines.append(StyledLine('; '.join(hit['reasons'][:3]), Tone.PREFERRED))
        if len(hits) > 6:
            lines.append(StyledLine(f'+{len(hits) - 6} more; full list in shop-latest.json'))
    elif result['issues']:
        lines = [StyledLine(f'Shop check incomplete — {count} items checked', Tone.WARNING)]
    else:
        lines = [StyledLine(f'No shopping targets found — {vendors} ({count} items checked)', Tone.METADATA)]
    if result['issues']:
        lines.append(StyledLine(f'{len(result["issues"])} read/decode issues; result is incomplete', Tone.WARNING))
    return lines


class ShopWorker:
    def __init__(
        self,
        source,
        executor,
        *,
        capture_lock,
        focused,
        display,
        output,
        before_request=lambda: None,
        clock=time.monotonic,
        capture=capture_shop,
        evaluate=assess,
        hit_seconds=HIT_SECONDS,
        quiet_seconds=QUIET_SECONDS,
        probe=capture_sentinel,
        auto=True,
        poll_interval=1.0,
        appraisal_active=lambda: False,
    ):
        self.source, self.executor = source, executor
        self.capture_lock, self.focused, self.display, self.output = capture_lock, focused, display, output
        self.before_request, self.clock, self.capture, self.evaluate = before_request, clock, capture, evaluate
        self.hit_seconds, self.quiet_seconds = hit_seconds, quiet_seconds
        self.probe, self.auto, self.poll_interval, self.appraisal_active = probe, auto, poll_interval, appraisal_active
        self.lock = threading.Lock()
        self.job = None  # 'scan' | 'poll' | None; one memory reader at a time
        self.manual_pending = False
        self.visible = None
        self.expires = 0.0
        self.stock_bound = False  # visible result is hidden early once its stock leaves memory
        self.generation = 0
        self.last_request = -math.inf
        self.last_poll = -math.inf
        self.next_poll_delay = poll_interval
        self.stock_state = None
        self.sentinel = None  # key of the stock the last result describes
        self.last_result = None
        self.attempts = {}  # stock key (as text) -> failed automatic scans
        self.future = None
        skill_targets()  # Warm the tiny rule catalog before the first hotkey.

    @property
    def busy(self):
        return self.job is not None

    # -- manual Win+D -------------------------------------------------------------------------

    def request(self, requested_at, now):
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1:
            return False
        with self.lock:
            if now - self.last_request < 0.35:
                return False
            self.last_request = now
            self.attempts.clear()
            if self.job == 'scan':
                return False
            if self.job == 'poll':
                self.manual_pending = True  # the running poll hands over to a scan
                return True
            self.job = 'scan'
            generation = self._begin_scan(manual=True)
        self.before_request()
        self.future = self.executor.submit(self._run, generation, True)
        return True

    def _begin_scan(self, *, manual):
        """Under self.lock: bump the generation and show progress for manual scans."""
        self.generation += 1
        if manual:
            self.visible = [StyledLine('Checking loaded shop stock…', Tone.METADATA)]
            self.expires = self.clock() + self.quiet_seconds
            self.stock_bound = False
        return self.generation

    # -- automatic watcher --------------------------------------------------------------------

    def poll(self, now):
        """Submit one cheap stock probe when due; returns whether one was started."""
        if not self.auto:
            return False
        with self.lock:
            if self.job is not None or now - self.last_poll < self.next_poll_delay:
                return False
            self.last_poll = now
            self.job = 'poll'
        self.future = self.executor.submit(self._poll)
        return True

    def _poll(self):
        scan = None
        try:
            if self.appraisal_active():
                return  # never fight Alt+D for the memory reader or the OSD
            with self.capture_lock:
                if self.appraisal_active():
                    return
                self.source.ensure_connected()
                if not self.focused(self.source.images):
                    with self.lock:
                        self._hide_stock_bound()
                    return
                probe = self.probe(self.source.pid, self.source.images, self.source.capture)
            scan = self._observe(probe)
        except Exception as exc:
            LOG.debug('Shop probe skipped: %s', exc)
        finally:
            with self.lock:
                manual = self.manual_pending
                self.manual_pending = False
                if manual:
                    scan = self._begin_scan(manual=True)  # Win+D arrived mid-poll: run it as a manual scan
                self.job = 'scan' if scan is not None else None
        if scan is not None:
            if manual:
                self.before_request()
            self._run(scan, manual)

    def _observe(self, probe):
        """Apply the watcher rules to one probe; returns a generation to scan or None."""
        state, key = probe['state'], probe.get('key')
        with self.lock:
            if state != self.stock_state:
                vendors = ', '.join(probe.get('vendors', []))
                LOG.info('Shop stock %s%s', state, f' ({vendors})' if vendors else '')
            self.stock_state = state
            self.next_poll_delay = self.poll_interval * (AWAY_BACKOFF if state == 'away' else 1)
            if state != 'loaded':
                self._hide_stock_bound()
                return None
            if key == self.sentinel:
                return None  # same stock (e.g. Trade closed and reopened): already checked and shown
            self._hide_stock_bound()
            attempts = self.attempts.get(repr(key), 0)
            if attempts >= AUTO_ATTEMPTS:
                return None
            self.attempts[repr(key)] = attempts + 1
            return self._begin_scan(manual=False)

    def _hide_stock_bound(self):
        """Under self.lock: drop a result whose stock is gone."""
        if self.stock_bound:
            self.visible, self.stock_bound = None, False

    def lease(self, result):
        return self.hit_seconds if result.get('hits') else self.quiet_seconds

    # -- the scan -----------------------------------------------------------------------------

    def _run(self, generation, manual):
        started = self.clock()
        result: dict[str, Any]
        try:
            with self.capture_lock:
                if self.clock() - started > 1:
                    raise ValueError('Shop request expired while waiting; press Win+D again')
                self.source.ensure_connected()
                if not self.focused(self.source.images):
                    raise ValueError('D2R is not focused')
                record = self.capture(self.source.pid, self.source.images, self.source.capture)
            result = self.evaluate(record)
            if result.get('issues'):
                publish(self.output / 'shop-diagnostics.json', {'record': record, 'result': result})
            if not self.focused(self.source.images):
                raise ValueError('D2R focus changed during scan')
        except Exception as exc:
            LOG.exception('Shop check failed')
            result = {'state': 'failed', 'error': str(exc)}
        result.update(finished_at=timestamp(), elapsed_ms=round((self.clock() - started) * 1000, 1), manual=manual)
        try:
            publish(self.output / 'shop-latest.json', result)
            LOG.info('Shop check: %s', result)
            with self.lock:
                if result['state'] != 'failed':
                    self.sentinel, self.last_result = result.get('sentinel'), result
                    self.attempts.pop(repr(self.sentinel), None)
                if self.generation != generation:
                    return
                if result['state'] == 'failed' and not manual:
                    return  # the watcher retries quietly; only Win+D reports failures
                self.visible = result_lines(result)
                self.stock_bound = result.get('sentinel') is not None
                self.expires = self.clock() + self.lease(result)
        finally:
            with self.lock:
                self.job = None

    # -- OSD ----------------------------------------------------------------------------------

    def dismiss(self):
        with self.lock:
            self.generation += 1
            self.visible, self.stock_bound = None, False

    def tick(self):
        with self.lock:
            if self.visible is None:
                return
            lines = self.visible
            expires = self.expires
        try:
            focused = self.focused(self.source.images)
        except Exception:
            LOG.exception('Shop OSD focus check failed')
            focused = False
        if self.clock() >= expires or not focused:
            self.dismiss()
            self.display([])
        else:
            self.display(lines)
