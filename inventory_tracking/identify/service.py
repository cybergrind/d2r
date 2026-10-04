"""Identify watcher: assess items right after Cain (or a scroll) identifies them.

Once a second in town (five seconds elsewhere) the worker reads the identified flag
of every magic-or-better item in the main inventory and the Horadric Cube. Items that were unidentified on
the previous read and are identified now are read in full, decoded and run through
the same offline knowledge base Alt+D uses; one OSD summary and one desktop
notification give each a verdict — keep, check or vendor — with the reason (value
watch, build use, trade tier, leveling use, asks) and its best-rolled stats. Owned copies
from the collection database are named in the reason; a build-use-only keep becomes a
check when a copy that rolls at least as well is already owned (appraisal/owned.py).
"""

import logging
import math
import re
import threading
import time
from contextlib import nullcontext
from typing import Any

from inventory_tracking.appraisal.owned import AT_LEAST_AS_GOOD, multiple_copy_use, owned_summary
from inventory_tracking.appraisal.presentation import item_tone
from inventory_tracking.appraisal.triage import LABELS, TONES, description
from inventory_tracking.common import LOG, timestamp
from inventory_tracking.identify.attention import actionable_roles, role_reason, starter_only
from inventory_tracking.identify.capture import capture_inventory_state, capture_records, decode_records
from inventory_tracking.presentation import StyledLine, Tone
from inventory_tracking.reports import publish


AWAY_BACKOFF = 5
SHOWN_ITEMS = 8
HIT_SECONDS = 20  # OSD lease when something valuable or in demand was identified
QUIET_SECONDS = 10
PROGRESS_SECONDS = 1  # the "Assessing…" line is a blink, not a status
SLOW_PROBE_MS = 250  # a poll slower than this is logged at INFO instead of DEBUG
CAPTURE_RETRIES = 2  # rereads when the game changed memory mid-read; the items are lost otherwise
CHANGED_DURING_READ = ('Unstable item snapshot', 'changed during read')


STAT_ABBREVIATIONS = (
    ('% Faster Cast Rate', ' FCR'),
    ('% Faster Hit Recovery', ' FHR'),
    ('% Faster Run/Walk', ' FRW'),
    ('% Increased Attack Speed', ' IAS'),
    ('% Better Chance of Getting Magic Items', ' MF'),
    ('% Extra Gold from Monsters', ' GF'),
    ('Fire Resist ', 'FR '),
    ('Cold Resist ', 'CR '),
    ('Lightning Resist ', 'LR '),
    ('Poison Resist ', 'PR '),
    ('All Resistances ', '@ '),
    (' to Attack Rating', ' AR'),
    (' to Strength', ' str'),
    (' to Dexterity', ' dex'),
    (' to Vitality', ' vit'),
    (' to Energy', ' ene'),
    (' to Life', ' life'),
    (' to Mana', ' mana'),
    ('% Life stolen per hit', ' LL'),
    ('% Mana stolen per hit', ' ML'),
    (' to All Skills', ' all skills'),
)
ANNOTATION = re.compile(r'\s*\([^)]*\)|\s*\[[^\]]*\]')
CLASS_SKILLS = re.compile(r'\+(\d+) to (\w+) Skill Levels')
VERDICT_TONES = {**TONES, 'keep': Tone.VALUABLE, 'check': Tone.DEMAND}
KEEP_IST = 1.0  # an estimate at or above one Ist is worth keeping on its own
CHECK_IST = 0.25


def compact_stat(text: str) -> str:
    """'Fire Resist +14% (5-40%) [T3; T1: 31-40%]' → 'FR +14%'."""
    text = ANNOTATION.sub('', text).strip()
    text = CLASS_SKILLS.sub(r'+\1 \2 skills', text)
    for long, short in STAT_ABBREVIATIONS:
        text = text.replace(long, short)
    return text


ELEMENTS = {'fire': 'Fire', 'light': 'Lightning', 'cold': 'Cold', 'pois': 'Poison', 'mag': 'Magic', '': ''}
RESISTS = ('fireresist', 'lightresist', 'coldresist', 'poisonresist')
# Stats a player scans for on jewelry, charms and armour; shown before other stats of the same tier.
WANTED_STATS = frozenset(
    (
        'item_addclassskills',
        'item_allskills',
        'item_addskill_tab',
        'item_fastercastrate',
        'item_fastergethitrate',
        'item_fastermovevelocity',
        'item_fasterattackrate',
        'maxhp',
        'maxmana',
        'item_magicbonus',
        'lifedrainmindam',
        'manadrainmindam',
        'tohit',
        'strength',
        'dexterity',
        *RESISTS,
    )
)


def notable_stats(observation, limit=3) -> list[str]:
    """The best-rolled decoded stats first (tier 1 before tier 3, untiered last).

    Elemental min/max damage components fold into one 'Adds x-y … Damage' entry ranked
    last, and four equal resistances become one '@' entry.
    """
    rows = [r for r in observation.get('decoded_stats', []) if r.get('status') == 'decoded' and r.get('text')]
    entries: list[tuple[int | None, bool, str]] = []  # tier, wanted, text
    damage: dict[str, dict[str, int]] = {}
    resists = {r['name']: r for r in rows if r.get('name') in RESISTS}
    all_resists = len(resists) == 4 and len({r.get('value') for r in resists.values()}) == 1
    for row in rows:
        name = row.get('name') or ''
        element = name.removesuffix('mindamage').removesuffix('maxdamage').removesuffix('mindam').removesuffix('maxdam')
        if element != name and element in ELEMENTS and isinstance(row.get('value'), int):
            damage.setdefault(element, {})['min' if 'min' in name else 'max'] = row['value']
            continue
        if name in ('coldlength', 'poisonlength'):
            continue
        if all_resists and name in RESISTS:
            if name == 'fireresist':
                entries.append((row.get('roll_tier'), True, f'@ +{row["value"]}%'))
            continue
        entries.append((row.get('roll_tier'), name in WANTED_STATS, compact_stat(row['text'])))
    for element, values in damage.items():
        label = f'{ELEMENTS[element]} Damage'.strip()
        entries.append((None, False, f'Adds {values.get("min", "?")}-{values.get("max", "?")} {label}'))
    entries.sort(key=lambda e: (e[0] is None, e[0] or 0, not e[1]))
    return [text for _, _, text in entries[:limit]]


def verdict_for(result, owned=None) -> tuple[str, str]:
    """(keep|check|vendor, reason) from what the offline assessment established.

    Keep: a value watch, a farming build use, a high/mid trade tier or a real estimate.
    Check: an evidenced conditional use, a leveling use or a small estimate.
    Starter roles alone stay quiet; the vendor bucket means no attention reason.
    A build use is only a check when an owned copy already rolls at least as well;
    trade reasons stay keep, since a second copy still sells.
    """
    if triage := result.get('triage'):
        return triage['verdict'], description(triage)
    assessment = result.get('assessment', {})
    roles = assessment.get('roles', [])
    estimate = (result.get('price_estimate') or {}).get('estimate_ist')
    for row in result.get('value_watch', [])[:1]:
        details = row['details']
        label = 'valuable' if details.get('priority') == 'valuable_candidate' else 'build demand'
        extra = details.get('roll_bucket') or details.get('stat_priority')
        return 'keep', f'{label}: {extra}' if extra and extra != '-' else label
    actionable = actionable_roles(result)
    matched = [r for r in actionable if r['status'] == 'matched']
    qualification = assessment.get('trade_qualification', {})
    if qualification.get('status') in ('candidate', 'premium'):
        return 'keep', qualification['reason']
    tier = assessment.get('trade_tier', {})
    if tier.get('status') in ('reviewed', 'conditional', 'market_supported') and tier.get('tier') in ('high', 'med'):
        return 'keep', f'trade tier {"mid" if tier["tier"] == "med" else tier["tier"]}'
    if estimate is not None and estimate >= KEEP_IST:
        return 'keep', f'asks ~{estimate:g} Ist'
    if matched:
        if owned and owned['count'] and owned['relation'] in AT_LEAST_AS_GOOD and not multiple_copy_use(result):
            return 'check', role_reason(matched, result)
        return 'keep', role_reason(matched, result)
    partial = [r for r in actionable if r['status'] == 'partial']
    if partial:
        return 'check', role_reason(partial, result, conditional=True)
    for use in assessment.get('leveling', []):
        if not use.get('generic') and use.get('tier') in ('high', 'med'):
            label = 'mid' if use['tier'] == 'med' else use['tier']
            return 'check', f'leveling {label}: {use["reason"].split(". ")[0].rstrip(".")}'
    if tier.get('tier') == 'low':
        return 'check', 'trade tier low'
    if estimate is not None and estimate >= CHECK_IST:
        return 'check', f'asks ~{estimate:g} Ist'
    failed = sum(1 for r in roles if r['status'] == 'failed')
    reasons = [f'no build use ({failed} rules failed)' if failed else 'no build use']
    if not roles:
        reasons = ['no build rules for this item']
    elif any(r['status'] in ('matched', 'partial') for r in roles):
        candidates = [r for r in roles if r['status'] in ('matched', 'partial')]
        reasons = [
            'no farming alert reason (starter-only build use)'
            if all(starter_only(r, result) for r in candidates)
            else 'no supported farming build use'
        ]
    reasons.append('no supported estimate' if estimate is None else f'asks ~{estimate:g} Ist')
    return 'vendor', '; '.join(reasons)


def item_summary(observation, result, owned=None) -> dict[str, Any]:
    """One row per identified item: verdict, the reason (owned copies included) and the stats that matter."""
    item = observation['item']
    name = item['name']
    if item.get('base_name') and item['base_name'] != name:
        name += f' ({item["base_name"]})'
    if observation['source'].get('container', {}).get('page') == 3:
        name += ' [cube]'
    verdict, reason = verdict_for(result, owned)
    if clause := owned_summary(owned):
        reason += f'; {clause}'
    return {
        **({'triage': result['triage']} if 'triage' in result else {}),
        'name': name,
        'rarity': item.get('rarity'),
        'tone': item_tone(item).value,
        'verdict': verdict,
        'reason': reason,
        'stats': notable_stats(observation),
        'estimate_ist': (result.get('price_estimate') or {}).get('estimate_ist'),
        'unit_id': observation['source'].get('unit_id'),
        **({'owned': owned} if owned is not None else {}),
    }


VERDICT_ORDER = ('keep', 'check', 'vendor')


def verdict_order(items):
    return ('sell', 'self', 'check', 'slow', 'vendor') if any('triage' in i for i in items) else VERDICT_ORDER


def counts(items) -> dict[str, int]:
    return {verdict: sum(1 for i in items if i['verdict'] == verdict) for verdict in verdict_order(items)}


def result_lines(result) -> list[StyledLine]:
    if result['state'] == 'failed':
        return [StyledLine('Identify assessment unavailable', Tone.WARNING), StyledLine(result['error'])]
    order = verdict_order(result['items'])
    items = sorted(result['items'], key=lambda i: order.index(i['verdict']))
    tally = counts(items)
    tone = next((VERDICT_TONES[v] for v in order if v != 'vendor' and tally[v]), Tone.METADATA)
    summary = ' · '.join(f'{tally[v]} {v}' for v in order)
    lines = [StyledLine(f'Identified {len(items)} — {summary}', tone)]
    # Only items with something particular get a row; vendor items are just counted.
    shown = [i for i in items if i['verdict'] not in ('vendor', 'slow')]
    for item in shown[:SHOWN_ITEMS]:
        stats = ' · '.join(item['stats']) or 'no decoded stats'
        lines.append(
            StyledLine(
                f'{LABELS.get(item["verdict"], item["verdict"].upper()):6s} {item["name"]}: {stats}', Tone(item['tone'])
            )
        )
        lines.append(
            StyledLine(f'       {item["reason"]}', (TONES if 'triage' in item else VERDICT_TONES)[item['verdict']])
        )
    if slow := [i for i in items if i['verdict'] == 'slow']:
        prices = [i.get('triage', {}).get('decision_ist') for i in slow]
        prices = [p for p in prices if type(p) in (int, float)]
        price_text = f', cheapest asks {min(prices):g}-{max(prices):g} Ist' if prices else ''
        lines.append(StyledLine(f'{len(slow)} slow{price_text} · details: Alt+D', TONES['slow']))
    if len(shown) > SHOWN_ITEMS:
        lines.append(StyledLine(f'+{len(shown) - SHOWN_ITEMS} more; full list in identify-latest.json'))
    if result['issues']:
        lines.append(StyledLine(f'{len(result["issues"])} read/decode issues; result is incomplete', Tone.WARNING))
    return lines


def describe(result) -> tuple[str, str] | None:
    """Desktop notification for the keep/check items; None when there is nothing particular."""
    order = verdict_order(result['items'])
    items = sorted(result['items'], key=lambda i: order.index(i['verdict']))
    worth = [f'{i["verdict"].upper()} {i["name"]} — {i["reason"]}' for i in items if i['verdict'] != 'vendor']
    if not worth:
        return None
    tally = counts(items)
    title = f'Identified {len(items)}: ' + ' · '.join(f'{tally[v]} {v}' for v in order)
    return title, '\n'.join(worth[:6])


def elapsed_ms(clock, since):
    return round((clock() - since) * 1000, 1)


class PhaseTiming:
    """Where a mass-identify pass spends its time: reader lock, memory read, decode, KB retrieval per item."""

    def __init__(self, items):
        self.items = items
        self.lock_wait_ms = self.capture_ms = self.decode_ms = self.retrieve_ms = self.total_ms = 0.0
        self.retrieve_max_ms = 0.0
        self.retrieve_max_item = None
        self.retrievals = []

    def retrieved(self, name, ms):
        self.retrievals.append({'name': name, 'ms': ms})
        self.retrieve_ms = round(self.retrieve_ms + ms, 1)
        if self.retrieve_max_item is None or ms > self.retrieve_max_ms:
            self.retrieve_max_ms, self.retrieve_max_item = ms, name
        LOG.debug('Identify retrieve %s: %s ms', name, ms)

    def as_dict(self):
        return dict(vars(self))

    def __str__(self):
        retrieved = len(self.retrievals)
        average = round(self.retrieve_ms / retrieved, 1) if retrieved else 0.0
        return (
            f'{self.items} items in {self.total_ms} ms — lock wait {self.lock_wait_ms}, capture {self.capture_ms}, '
            f'decode {self.decode_ms}, retrieve {self.retrieve_ms} ({retrieved} lookups, avg {average}, '
            f'max {self.retrieve_max_ms} {self.retrieve_max_item or "-"})'
        )


class IdentifyWorker:
    def __init__(
        self,
        source,
        executor,
        *,
        capture_lock,
        focused,
        display,
        output,
        retrieve,
        owned=lambda observation: None,
        request_scope=nullcontext,
        notify=lambda title, body: None,
        clock=time.monotonic,
        probe=capture_inventory_state,
        capture=capture_records,
        decode=decode_records,
        auto=True,
        poll_interval=1.0,
        appraisal_active=lambda: False,
        hit_seconds=HIT_SECONDS,
        quiet_seconds=QUIET_SECONDS,
        retry_delay=0.1,
        lookup_executor=None,
    ):
        self.source, self.executor = source, executor
        self.capture_lock, self.focused, self.display, self.output = capture_lock, focused, display, output
        self.retrieve, self.owned, self.request_scope = retrieve, owned, request_scope
        self.notify, self.clock = notify, clock
        self.probe, self.capture, self.decode = probe, capture, decode
        self.auto, self.poll_interval, self.appraisal_active = auto, poll_interval, appraisal_active
        self.hit_seconds, self.quiet_seconds = hit_seconds, quiet_seconds
        self.retry_delay = retry_delay
        self.lookup_executor = lookup_executor  # runs one pass's KB lookups in parallel; None = one by one
        self.lock = threading.Lock()
        self.busy = False
        self.visible = None
        self.expires = 0.0
        self.generation = 0
        self.last_poll = -math.inf
        self.next_poll_delay = poll_interval
        self.unidentified: set[str] | None = None  # None until the inventory was read once
        self.last_result = None
        self.future = None

    # -- polling --------------------------------------------------------------------------------

    def poll(self, now):
        if not self.auto:
            return False
        with self.lock:
            if self.busy or now - self.last_poll < self.next_poll_delay:
                return False
            self.last_poll = now
            self.busy = True
        self.future = self.executor.submit(self._poll)
        return True

    def _poll(self):
        newly = []
        requested = self.clock()
        try:
            if self.appraisal_active():
                return
            with self.capture_lock:
                lock_wait = elapsed_ms(self.clock, requested)
                if self.appraisal_active():
                    return
                self.source.ensure_connected()
                if not self.focused(self.source.images):
                    return
                started = self.clock()
                probe = self.probe(self.source.pid, self.source.images, self.source.capture)
                probe_ms = elapsed_ms(self.clock, started)
            newly = self._observe(probe)
            LOG.log(
                logging.INFO if newly or probe_ms >= SLOW_PROBE_MS else logging.DEBUG,
                'Identify probe: %s, %d items in %s ms (lock wait %s ms)',
                probe['state'],
                len(probe.get('items', {})),
                probe_ms,
                lock_wait,
            )
        except Exception as exc:
            LOG.debug('Identify probe skipped: %s', exc)
            with self.lock:
                self.unidentified = None
        finally:
            if not newly:
                with self.lock:
                    self.busy = False
        if newly:
            LOG.info('Identified: %s', ', '.join(newly))
            self._assess(newly)

    def _observe(self, probe) -> list[str]:
        """Update the unidentified set; return the units that just became identified."""
        with self.lock:
            self.next_poll_delay = self.poll_interval * (AWAY_BACKOFF if probe['state'] == 'away' else 1)
            if probe['state'] != 'ok':
                self.unidentified = None
                return []
            items = probe['items']
            current = {unit_id for unit_id, item in items.items() if not item['identified']}
            previous, self.unidentified = self.unidentified, current
            if previous is None:
                return []
            return sorted(unit_id for unit_id in previous - current if unit_id in items)

    # -- assessment -----------------------------------------------------------------------------

    def _read(self, unit_ids, timing, requested):
        """Capture and decode; read again when the game changed memory during the read."""
        for attempt in range(1 + CAPTURE_RETRIES):
            with self.capture_lock:
                timing.lock_wait_ms += elapsed_ms(self.clock, requested)
                self.source.ensure_connected()
                phase = self.clock()
                record = self.capture(self.source.pid, self.source.images, self.source.capture, unit_ids)
                timing.capture_ms += elapsed_ms(self.clock, phase)
            phase = self.clock()
            observations, issues = self.decode(record)
            timing.decode_ms += elapsed_ms(self.clock, phase)
            changed = [issue for issue in issues if any(marker in issue for marker in CHANGED_DURING_READ)]
            if not changed or attempt == CAPTURE_RETRIES:
                return record, observations, issues
            LOG.info('Identify read changed under it (%s); reading again', changed[0])
            time.sleep(self.retry_delay)
            requested = self.clock()
        raise AssertionError('unreachable')

    def _lookup(self, observation):
        """(evidence, error, ms) of one KB lookup; runs on a lookup thread, so it owns its request scope."""
        started = self.clock()
        try:
            with self.request_scope():
                return self.retrieve(observation), None, elapsed_ms(self.clock, started)
        except Exception as exc:
            return None, exc, elapsed_ms(self.clock, started)

    def _lookups(self, observations):
        if self.lookup_executor is None:
            return map(self._lookup, observations)
        return self.lookup_executor.map(self._lookup, observations)

    def _assess(self, unit_ids):
        started = self.clock()
        timing = PhaseTiming(len(unit_ids))
        with self.lock:
            self.generation += 1
            generation = self.generation
            self.visible = [StyledLine(f'Assessing {len(unit_ids)} identified items…', Tone.METADATA)]
            self.expires = self.clock() + PROGRESS_SECONDS
        result: dict[str, Any]
        try:
            record, observations, issues = self._read(unit_ids, timing, started)
            from inventory_tracking.corpus.store import persist

            for observation in observations:
                try:
                    persist(self.output, observation)
                except (OSError, TypeError, ValueError) as exc:
                    LOG.warning('Could not retain identified observation: %s', exc)
                    issues.append(f'Corpus persistence failed: {exc}')
            items = []
            for observation, (evidence, error, ms) in zip(observations, self._lookups(observations), strict=True):
                name = observation['item'].get('name', 'item')
                phase = self.clock()
                try:
                    if error is not None:
                        raise error
                    items.append(item_summary(observation, evidence, self.owned(observation)))
                except Exception as exc:
                    LOG.warning('Identify assessment of %s failed: %s', name, exc)
                    issues.append(f'{name}: {exc}')
                finally:
                    timing.retrieved(name, round(ms + elapsed_ms(self.clock, phase), 1))
            result = {'state': 'complete' if not issues else 'partial', 'items': items, 'issues': issues}
            if issues:
                publish(self.output / 'identify-diagnostics.json', {'record': record, 'result': result})
        except Exception as exc:
            LOG.exception('Identify assessment failed')
            result = {'state': 'failed', 'error': str(exc), 'items': [], 'issues': []}
        timing.total_ms = elapsed_ms(self.clock, started)
        result.update(
            finished_at=timestamp(), elapsed_ms=timing.total_ms, unit_ids=list(unit_ids), timing=timing.as_dict()
        )
        try:
            publish(self.output / 'identify-latest.json', result)
            LOG.info('Identify timing: %s', timing)
            LOG.info('Identify assessment: %s', result)
            with self.lock:
                self.last_result = result
                if self.generation != generation:
                    return
                self.visible = result_lines(result)
                hits = any(i['verdict'] != 'vendor' for i in result['items'])
                self.expires = self.clock() + (self.hit_seconds if hits else self.quiet_seconds)
            notification = describe(result) if result['state'] != 'failed' else None
            if notification is not None:
                self.notify(*notification)
        finally:
            with self.lock:
                self.busy = False

    # -- OSD ------------------------------------------------------------------------------------

    def dismiss(self):
        """Hide and cancel: a result that finishes afterwards is not shown (Alt+D, shutdown)."""
        with self.lock:
            self.generation += 1
            self.visible = None

    def tick(self):
        with self.lock:
            if self.visible is None:
                return
            lines, expires = self.visible, self.expires
        try:
            focused = self.focused(self.source.images)
        except Exception:
            LOG.exception('Identify OSD focus check failed')
            focused = False
        if self.clock() >= expires:
            # Expiry only hides: the progress blink must not cancel the result it announces.
            with self.lock:
                if self.visible is lines:
                    self.visible = None
            self.display([])
        elif not focused:
            # Focus loss only hides too: a failed focus probe during the progress blink used to
            # cancel the whole pass. The card returns with the focus while its lease lasts.
            self.display([])
        else:
            self.display(lines)
