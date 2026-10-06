"""Host Alt+D/Win+S/Win+D/Win+C worker. Start `serve`, then use the compositor's `request` bindings.

Datagrams: a bare monotonic timestamp requests an Alt+D appraisal; `collect <timestamp>`
requests a Win+S inventory collection (`request --collect`: every container, mercenary
equipment and the character sheet); `equipped <timestamp>` (`request --equipped`, no
binding) records only what the character and the mercenary wear. `shop <timestamp>` requests
a Win+D shop check (`request --shop`). `level <timestamp>` (`request --level`, Win+C) shows
the level map card again (fresh position, any level; a double press pins or unpins it) and
dumps the current level's room/unit structures for research (runs/level/). `macro <timestamp>`
(`request --macro`, Win+X) runs the macro for where the character is, or cancels a running one
(inventory_tracking/macros/plan.md). The level card is
drawn on the HUD canvas (inventory_tracking/hud, started with the overlay), so it can show
next to an Alt+D assessment. With `--shop-auto` (default) the worker also watches loaded
vendor stock and scans it by itself when its first gear item changes; see
inventory_tracking/shop/README.md. With `--stash-auto` (default) it also runs a Win+S
collection by itself every time the stash panel is closed, and with `--identify-auto`
(default) it assesses every inventory or cube item the moment it becomes identified (Cain's
identify all, or a scroll) and shows the summary on the OSD. With `--level-guide` (default)
entering a guided level (levels/handlers/) shows an arrow to its target. With `--terror-probe`
(default) it records monster sightings and kills to terror-probe.jsonl for Terror Zone research
(inventory_tracking/terror/probe.py); Win+C also writes a mark there.
"""

import argparse
import fcntl
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext, suppress
from functools import partial
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from inventory_tracking.appraisal.cache import database_revision
from inventory_tracking.appraisal.capture import AppraisalCapture, RecentFocus
from inventory_tracking.appraisal.loop_timing import PassTimer
from inventory_tracking.appraisal.material_sets import recorded_set
from inventory_tracking.appraisal.owned import owned_copies
from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.appraisal.published_backend import (
    PublicationRefresher,
    PublishedAppraisal,
    prepare_processes,
    warm_publication,
)
from inventory_tracking.appraisal.retrieval_process import KeepWarm, RetrievalGroup, RetrievalProcess
from inventory_tracking.appraisal.text import value_watch_lines
from inventory_tracking.appraisal.worker import AppraisalWorker
from inventory_tracking.collection.export import DEFAULT_HTML as COLLECTION_HTML
from inventory_tracking.collection.service import (
    DEFAULT_OUTPUT as COLLECTION_OUTPUT,
    EQUIPMENT_PREFIX,
    REQUEST_PREFIX,
    Collector,
)
from inventory_tracking.collection.store import DEFAULT_DATABASE as COLLECTION_DATABASE
from inventory_tracking.collection.watch import StashWatcher
from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.config import APPRAISAL, SHOW_ITEMS
from inventory_tracking.hud.process import card_widgets, guide_widgets, hud_process, loot_widgets, terror_widgets
from inventory_tracking.hud.scene import DEFAULT_SCENE, publish_layer
from inventory_tracking.identify.service import IdentifyWorker
from inventory_tracking.levels.dump import (
    DEFAULT_OUTPUT as LEVEL_OUTPUT,
    REQUEST_PREFIX as LEVEL_PREFIX,
    LevelDumper,
)
from inventory_tracking.levels.evidence import DEFAULT_EVIDENCE, EvidenceLog
from inventory_tracking.levels.guide import LevelGuide
from inventory_tracking.levels.memory import observe_walkable, observe_waypoints
from inventory_tracking.levels.walls import WallLibrary
from inventory_tracking.loot.watch import RuneWatcher
from inventory_tracking.macros.runner import REQUEST_PREFIX as MACRO_PREFIX, MacroRunner
from inventory_tracking.native.session import GameNotReady, GameProcessUnavailable
from inventory_tracking.osd.__main__ import positive_float
from inventory_tracking.reports import create_run, publish
from inventory_tracking.shop.service import REQUEST_PREFIX as SHOP_PREFIX, ShopWorker, triage_stock
from inventory_tracking.terror.bosses import BossTracker
from inventory_tracking.terror.probe import TerrorProbe
from inventory_tracking.terror.tracker import ZoneTracker
from inventory_tracking.tracking.panels import observe_panels
from inventory_tracking.tracking.reader import LiveReader
from pricing.knowledge.publication import DEFAULT_STORE
from pricing.triage.engine import revision as triage_revision
from pricing.triage.runtime import detail as triage_detail, fast_retrieve as triage_retrieve, warm as triage_warm


def owned_evidence(database):
    """Owned copies of an observed item from the collection; None when the database is unreadable."""

    def lookup(observation):
        try:
            owned = owned_copies(observation, database)
            basket = recorded_set(observation, database)
            return {**(owned or {}), 'material_set': basket} if basket else owned
        except sqlite3.Error as exc:
            LOG.warning('Owned-copy lookup failed: %s', exc)
            return None

    return lookup


def with_owned(retrieve, owned):
    def retrieve_owned(observation):
        return {**retrieve(observation), 'owned': owned(observation)}

    return retrieve_owned


def process_retrieval(process, backend, database, recent=None):
    """KB retrieval run in `process`; a published backend's request scope travels as plain values."""

    def retrieve(observation):
        if recent is not None:
            recent.remember(observation)
        if backend is None:
            return process.call(triage_detail, observation, database)
        return process.call(triage_detail, observation, database, backend.pinned())

    return retrieve


def identify_retrieval(fast, detail, backend, database):
    """Keep legacy work out of the identify queue, including unrouted item types."""
    fallback = process_retrieval(detail, backend, database)

    def retrieve(observation):
        result = fast.call(triage_retrieve, observation)
        return result if result is not None else fallback(observation)

    return retrieve


def warm_identify_lookup(recent):
    def touch(process):
        process.call(triage_warm, recent.next())

    return touch


class RecentObservations:
    """The last few looked-up items, replayed in turn to keep idle retrieval processes warm."""

    def __init__(self, seed=(), *, size=8):
        self.lock = threading.Lock()
        self.items = deque(seed, maxlen=size)

    def remember(self, observation):
        with self.lock:
            self.items.append(observation)

    def next(self):
        with self.lock:
            if not self.items:
                return None
            self.items.rotate(-1)
            return self.items[-1]


def stored_observations(output, *, limit=8):
    """Distinct items of the newest earlier Alt+D requests under `output`: warm-up lookups for a new service."""
    found = {}
    for path in sorted(output.glob('*/request-*/frozen.json'), reverse=True):
        try:
            observation = json.loads(path.read_text())['observation']
            found.setdefault((observation['item'].get('rarity'), observation['item'].get('name')), observation)
        except OSError, ValueError, KeyError, TypeError:
            continue
        if len(found) == limit:
            break
    return list(found.values())


def warm_lookup(backend, database, recent):
    """`touch` for `KeepWarm`: rerun a recent lookup in the given process and drop the result."""

    def touch(process):
        observation = recent.next()
        if observation is None:
            return
        with backend.request_scope() if backend else nullcontext():
            process_retrieval(process, backend, database)(observation)

    return touch


@contextmanager
def refreshing(backend, processes, store):
    """Adopt newly published KB generations in the background (none without a publication store)."""
    if backend is None:
        yield
        return
    stopped = threading.Event()
    prepare = prepare_processes(processes, store, stopped=stopped)
    try:
        with PublicationRefresher(backend, prepare, interval=APPRAISAL.publication_poll_interval):
            yield
    finally:
        stopped.set()


def collection_revision(database):
    """Part of the Alt+D cache key: a new Win+S capture invalidates cached owned-copy comparisons."""
    with suppress(OSError):
        return database.stat().st_mtime_ns
    return None


def notify(title, body):
    with suppress(OSError, subprocess.SubprocessError):
        subprocess.run(['notify-send', '--app-name=D2R appraisal', title, body], timeout=2, check=False)


def publish_request(directory, record: dict[str, Any], *, notifications=True):
    """Called under the worker publication lock after freshness checks."""
    request_dir = directory / f'request-{record["request_id"]}'
    request_dir.mkdir(exist_ok=True)
    record = dict(record, updated_at=timestamp())
    diagnostics = record.pop('diagnostics', None)
    if diagnostics is not None:
        publish(request_dir / 'panel-diagnostics.json', diagnostics)
        record['diagnostics_file'] = str(request_dir / 'panel-diagnostics.json')
    frozen = record.pop('frozen', None)
    if frozen is not None:
        publish(request_dir / 'frozen.json', frozen)
        record['snapshot_file'] = str(request_dir / 'frozen.json')
    publish(request_dir / 'report.json', record)
    publish(directory / 'latest.json', record)
    if record['state'] in ('complete', 'rejected'):
        assessment = ItemAssessment.from_record(record, frozen)
        text = assessment.to_text()
        (request_dir / 'appraisal.txt').write_text(text, encoding='utf-8')
        LOG.info('%s', text, extra={'styled_message': assessment.to_rich()})
    else:
        LOG.info('Appraisal request %s: %s', record['request_id'], record['state'])
    if not notifications:
        return
    if record['state'] == 'complete':
        extraction = record['result']['extraction']
        item = extraction['item']
        stats = '; '.join(s['text'] for s in extraction.get('decoded_stats', [])[:4])
        if not stats:
            stats = '; '.join(a['label'].replace('{{value}}', str(a['value'])) for a in item['affixes'][:4])
        estimate = record['result'].get('price_estimate') or {}
        value = estimate.get('estimate_ist')
        price = f'Offline ask estimate: ~{value:g} Ist' if value is not None else 'Price estimate unavailable'
        watches = value_watch_lines(record['result'])
        priority = watches[0] if watches else 'review required'
        notify(f'{item["name"]} — {priority}', f'{stats or "No supported stats"}\n{price}. Report: {request_dir}')
    elif record['state'] == 'rejected':
        detail = record['reason']
        if record.get('diagnostics_file'):
            detail += '\nPanel diagnostics saved for investigation.'
        notify('Appraisal unavailable', detail)


def dispatch(
    data: bytes,
    now: float,
    worker,
    collector,
    shop=None,
    identify=None,
    level=None,
    guide=None,
    terror=None,
    disagree=None,
    macro=None,
) -> bool:
    """Route `shop <t>`, `collect <t>`, `equipped <t>`, `level <t>` and bare Alt+D timestamps to their workers.

    An accepted Alt+D takes the OSD: a shop result or an identify summary still showing
    is dismissed at once, so the hotkey doubles as "close that" even over an empty cell.
    """
    try:
        text = data.decode('ascii').strip()
        if text.startswith('disagree '):
            requested = float(text[len('disagree ') :])
            return bool(disagree and 0 <= now - requested <= 1 and disagree())
        if text.startswith(MACRO_PREFIX):
            # Win+X: run the macro for where the character is; a press while one runs cancels it.
            return macro is not None and macro.request(float(text[len(MACRO_PREFIX) :]), now)
        if text.startswith(SHOP_PREFIX):
            return shop is not None and shop.request(float(text[len(SHOP_PREFIX) :]), now)
        if text.startswith(LEVEL_PREFIX):
            # Win+C: switch the level map's view or show it again (double press: pin/unpin it), then dump quietly.
            requested = float(text[len(LEVEL_PREFIX) :])
            if not 0 <= now - requested <= 1:
                return False
            if terror is not None:
                terror.mark(now)  # research: lets a Herald on screen be matched to its sighting
            shown = guide is not None and guide.press(requested)  # a double press toggles the pinned map
            dumped = level is not None and level.request(requested, now, announce=not shown)
            return shown or dumped
        if text.startswith(REQUEST_PREFIX):
            return collector.request(float(text[len(REQUEST_PREFIX) :]), now)
        if text.startswith(EQUIPMENT_PREFIX):
            return collector.request(float(text[len(EQUIPMENT_PREFIX) :]), now, scope='equipment')
        accepted = worker.request(float(text), now)
        if accepted and shop is not None:
            shop.dismiss()
        if accepted and identify is not None and identify.visible is not None:
            identify.dismiss()
            identify.display([])
        return accepted
    except ValueError, UnicodeError:
        return False


def serve(args):
    directory, report = create_run(args.output)
    publish(directory / 'report.json', report)
    try:
        with log_to_file(directory / 'probe.log'):
            return run_service(args, directory, report)
    except KeyboardInterrupt:
        report.update(state='complete', finished_at=timestamp())
        return 130
    except Exception as exc:
        report.update(state='failed', error=str(exc), finished_at=timestamp())
        raise
    finally:
        publish(directory / 'report.json', report)


def wait_for_game(connect, directory, report):
    """Attach once D2R.exe exists and a character is in a game; other attach failures abort."""
    waiting = None
    while True:
        try:
            return connect()
        except (GameProcessUnavailable, GameNotReady) as exc:
            message = 'Waiting for a character in game' if isinstance(exc, GameNotReady) else 'Waiting for D2R.exe'
            if message != waiting:
                report.update(state='waiting', reason=str(exc))
                publish(directory / 'report.json', report)
                print(f'{message}. Reports: {directory}', flush=True)
                LOG.info('%s: %s', message, exc)
                waiting = message
            time.sleep(APPRAISAL.reconnect_delay)


def run_service(args, directory, report):
    endpoint = args.socket
    lock_path = endpoint.with_suffix('.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('An appraisal worker is already running') from None
        # Only our private, fixed-purpose runtime socket is replaced under its lock.
        if endpoint.exists():
            endpoint.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(endpoint))
            endpoint.chmod(0o600)
            server.settimeout(APPRAISAL.poll_interval)
            try:
                reader = LiveReader(directory, pid=args.pid)

                def connect():
                    attachment = Path(mkdtemp(prefix='attachment-', dir=directory))
                    try:
                        connection = reader.connect(attachment)
                    except GameNotReady:
                        # Menu-time retries would otherwise leave one full image capture every few seconds.
                        shutil.rmtree(attachment, ignore_errors=True)
                        raise
                    report.pop('reason', None)
                    report.update(
                        state='ready',
                        game_identity=connection[1]['identity'],
                        socket=str(endpoint),
                        attachment_directory=str(attachment),
                    )
                    publish(directory / 'report.json', report)
                    return connection

                backend = PublishedAppraisal(args.publication_store) if args.publication_store else None
                warm = ()
                if backend:
                    try:
                        backend.start()
                    except ValueError as error:
                        raise ValueError(
                            f'{error}; run uv run --offline python -m pricing.knowledge.publication'
                        ) from error
                    startup_generation = backend.serving[0].runtime.generation
                    warm = (warm_publication, (args.publication_store, startup_generation))
                pid, images, capture = wait_for_game(connect, directory, report)
                print(f'Ready for Alt+D. Reports: {directory}', flush=True)
                source = AppraisalCapture(pid, images, capture, reconnect=connect)
                recent = RecentObservations(stored_observations(args.output))

                with (
                    hud_process(args.hud_scene, args.osd, directory / 'hud.log'),
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='appraisal-kb') as pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='collection') as collection_pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='shop') as shop_pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='identify') as identify_pool,
                    ThreadPoolExecutor(
                        max_workers=APPRAISAL.identify_lookup_processes, thread_name_prefix='identify-lookup'
                    ) as identify_lookup_pool,
                    # Separate processes: KB lookups would otherwise hold this process's GIL and stall the loop.
                    RetrievalProcess(*warm) as appraisal_lookups,
                    RetrievalGroup(
                        APPRAISAL.identify_lookup_processes, triage_warm, (recent.next(),)
                    ) as identify_lookups,
                    refreshing(backend, [appraisal_lookups], args.publication_store),
                    # Detail warm-up can take seconds. Unrouted identify items use this
                    # already-warm process rather than blocking the fast worker queues.
                    KeepWarm(
                        [appraisal_lookups],
                        warm_lookup(backend, args.database, recent),
                        interval=APPRAISAL.retrieval_keep_warm_interval,
                    ),
                    KeepWarm(
                        identify_lookups.processes,
                        warm_identify_lookup(recent),
                        interval=APPRAISAL.retrieval_keep_warm_interval,
                    ),
                ):
                    shop = None
                    identify = None
                    guide = None

                    def display_appraisal(record):
                        # Shop/identify results share the 'assessment' slot and take precedence; the
                        # level guide has its own slot, so it never hides an assessment.
                        if all(w is None or w.visible is None for w in (shop, identify)):
                            lines = ItemAssessment.from_record(record).to_osd() if record is not None else []
                            publish_layer(args.hud_scene, 'appraisal', card_widgets(lines))

                    retrieve = process_retrieval(appraisal_lookups, backend, args.database, recent)
                    focused = RecentFocus(seconds=APPRAISAL.focus_cache_seconds)
                    owned = owned_evidence(args.collection_database)
                    kb_revision = backend.cache_context if backend else lambda: database_revision(args.database)
                    worker = AppraisalWorker(
                        source,
                        with_owned(retrieve, owned),
                        lambda record: publish_request(directory, record, notifications=not args.osd),
                        pool,
                        display=display_appraisal if args.osd else None,
                        display_seconds=args.osd_seconds,
                        recheck_seconds=APPRAISAL.display_recheck_interval,
                        cache_seconds=args.cache_seconds,
                        cache_context=lambda: (
                            kb_revision(),
                            collection_revision(args.collection_database),
                            triage_revision(),
                        ),
                        request_scope=backend.request_scope if backend else nullcontext,
                    )
                    collector = Collector(
                        source,
                        args.collection_database,
                        args.collection_output,
                        collection_pool,
                        html=args.collection_html,
                        capture_lock=worker.capture_lock,
                        focused=focused,
                        notify=notify,
                    )

                    def disagree():
                        from inventory_tracking.appraisal.feedback import flag
                        from inventory_tracking.corpus.build import DATA

                        with worker.lock:
                            record = worker.visible
                            if not record:
                                notify('Flag a verdict', 'Show the item with Alt+D first.')
                                return False
                            try:
                                saved = flag(record, DATA, str(directory / f'request-{record["request_id"]}'))
                            except (OSError, ValueError, TypeError) as error:
                                LOG.warning('Cannot save verdict disagreement: %s', error)
                                notify('Verdict not saved', str(error))
                                return False
                        notify(
                            'Verdict flagged' if saved else 'Already flagged',
                            'Saved for review; your expected verdict is not assumed.',
                        )
                        LOG.info('Verdict disagreement: request %s, saved=%s', record['request_id'], saved)
                        return True

                    def suspend_appraisal():
                        with worker.lock:
                            worker.generation += 1
                            worker.hide()

                    def display_shop(lines):
                        if args.osd:
                            publish_layer(args.hud_scene, 'cards', card_widgets(lines))

                    def display_identify(lines):
                        # Its own layer: the shop card and the identify summary stack instead of
                        # overwriting (and clearing) each other.
                        if args.osd:
                            publish_layer(args.hud_scene, 'identify', card_widgets(lines, 'identify'))

                    shop = ShopWorker(
                        source,
                        shop_pool,
                        evaluate=lambda record: identify_lookups.call(triage_stock, record),
                        capture_lock=worker.capture_lock,
                        focused=focused,
                        display=display_shop,
                        output=directory,
                        before_request=suspend_appraisal,
                        auto=args.shop_auto,
                        poll_interval=args.shop_poll_seconds,
                        appraisal_active=lambda: worker.visible is not None or worker.pending(),
                    )
                    identify = IdentifyWorker(
                        source,
                        identify_pool,
                        capture_lock=worker.capture_lock,
                        focused=focused,
                        display=display_identify,
                        output=directory,
                        retrieve=identify_retrieval(identify_lookups, appraisal_lookups, backend, args.database),
                        request_scope=backend.request_scope if backend else nullcontext,
                        lookup_executor=identify_lookup_pool,
                        notify=notify,
                        auto=args.identify_auto,
                        poll_interval=args.identify_poll_seconds,
                        appraisal_active=lambda: worker.visible is not None or worker.pending(),
                    )
                    level = LevelDumper(source, args.level_output, capture_lock=worker.capture_lock, notify=notify)

                    def display_macro(lines):
                        if args.osd:
                            publish_layer(args.hud_scene, 'macro', card_widgets(lines, 'macro'))

                    macro = MacroRunner(
                        source,
                        capture_lock=worker.capture_lock,
                        saved_games=SHOW_ITEMS.saved_games,
                        display=display_macro,
                    )
                    # Per-game monster/Herald state: the Terror card and the level map shading.
                    zones = ZoneTracker(args.output / 'terror-games.json') if args.terror_probe else None
                    map_dots = partial(zones.map_dots, danger=APPRAISAL.danger_marks) if zones is not None else None
                    if args.level_guide:
                        guide = LevelGuide(
                            source,
                            capture_lock=worker.capture_lock,
                            focused=focused,
                            display=lambda lines: publish_layer(args.hud_scene, 'levels', guide_widgets(lines)),
                            seconds=APPRAISAL.level_guide_seconds,
                            poll_interval=APPRAISAL.level_guide_poll_interval,
                            evidence=EvidenceLog(args.level_evidence).save,
                            observe_walls=observe_walkable if APPRAISAL.level_walls else None,
                            library=WallLibrary() if APPRAISAL.level_walls else None,
                            visited_rooms=zones.visited_rooms if zones is not None else None,
                            map_dots=map_dots,
                            on_rooms=zones.level_layout if zones is not None else None,
                            observe_waypoints=observe_waypoints,
                            pinned=APPRAISAL.level_guide_pinned,
                        )
                    runes = None
                    if args.rune_marks and args.osd:
                        runes = RuneWatcher(
                            source,
                            capture_lock=worker.capture_lock,
                            focused=focused,
                            display=lambda lines: publish_layer(args.hud_scene, 'loot', loot_widgets(lines)),
                            poll_interval=APPRAISAL.rune_poll_interval,
                            minimum=APPRAISAL.rune_minimum,
                            shrine_types=frozenset(APPRAISAL.shrine_marks),
                            super_chests=APPRAISAL.super_chest_marks,
                        )
                    terror = None
                    if args.terror_probe:
                        terror = TerrorProbe(
                            source,
                            directory / 'terror-probe.jsonl',
                            capture_lock=worker.capture_lock,
                            poll_interval=APPRAISAL.terror_probe_interval,
                            summary_seconds=APPRAISAL.terror_summary_seconds,
                            tracker=zones,
                            display=(
                                (lambda lines: publish_layer(args.hud_scene, 'terror', terror_widgets(lines)))
                                if APPRAISAL.terror_card and args.osd
                                else None
                            ),
                            focused=focused,
                            show_unconfirmed=APPRAISAL.terror_card_unconfirmed,
                            bosses=BossTracker(args.output / 'boss-kills.json') if APPRAISAL.boss_stats else None,
                            danger=APPRAISAL.danger_marks,
                            elites=APPRAISAL.elite_line,
                        )
                    stash = None
                    if args.stash_auto:
                        stash = StashWatcher(
                            lambda: observe_panels(source.pid, source.images),
                            lambda now: collector.request(now, now, trigger='stash-closed'),
                            poll_interval=args.stash_poll_seconds,
                        )
                    watching = 'watching vendor stock' if args.shop_auto else 'no automatic shop watch'
                    stash_note = 'collecting on stash close' if stash else 'no stash watch'
                    identify_note = 'assessing on identify' if args.identify_auto else 'no identify watch'
                    print(
                        f'Ready for Alt+D, Win+S, Win+D and Win+C ({watching}; {stash_note}; {identify_note}). '
                        f'Collection database: {args.collection_database}',
                        flush=True,
                    )
                    timer = PassTimer(APPRAISAL.slow_loop_seconds)
                    try:
                        while True:
                            with timer.step('appraisal'):
                                worker.tick()
                            with timer.step('shop'):
                                shop.tick()
                                shop.poll(time.monotonic())
                            with timer.step('identify'):
                                identify.tick()
                                identify.poll(time.monotonic())
                            if stash is not None:
                                with timer.step('stash'):
                                    stash.poll(time.monotonic())
                            if guide is not None:
                                with timer.step('level map'):
                                    guide.tick()
                                    guide.poll(time.monotonic())
                            if runes is not None:
                                with timer.step('runes'):
                                    runes.tick()
                                    runes.poll(time.monotonic())
                            if terror is not None:
                                with timer.step('terror probe'):
                                    terror.poll(time.monotonic())
                                    terror.tick()
                            with timer.step('macro'):
                                macro.poll(time.monotonic())
                            try:
                                data = server.recv(256)
                            except TimeoutError:
                                data = None
                            if data is not None:
                                with timer.step('hotkey'):
                                    dispatch(
                                        data,
                                        time.monotonic(),
                                        worker,
                                        collector,
                                        shop,
                                        identify,
                                        level,
                                        guide,
                                        terror,
                                        disagree=disagree,
                                        macro=macro,
                                    )
                            timer.finish()
                    finally:
                        macro.close()
                        shop.dismiss()
                        identify.dismiss()
                        if guide is not None:
                            guide.dismiss()
                        for producer in ('appraisal', 'cards', 'identify', 'levels', 'loot', 'macro', 'terror'):
                            publish_layer(args.hud_scene, producer, [])
                        for pending in (shop.future, identify.future):
                            if pending:
                                pending.cancel()
                        with worker.lock:
                            worker.generation += 1
                            worker.hide()
                        if worker.future:
                            worker.future.cancel()
            except KeyboardInterrupt:
                report.update(state='complete', finished_at=timestamp())
            except Exception as exc:
                report.update(state='failed', error=str(exc), finished_at=timestamp())
                raise
            finally:
                publish(directory / 'report.json', report)
                endpoint.unlink(missing_ok=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('serve', 'request'))
    parser.add_argument(
        '--socket',
        type=Path,
        default=Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'd2r-appraisal.sock',
    )
    parser.add_argument('--output', type=Path, default=Path('inventory_tracking/runs/alt-d'))
    knowledge = parser.add_mutually_exclusive_group()
    knowledge.add_argument('--database', type=Path, help='Explicit legacy/test index; bypass publication selection')
    knowledge.add_argument('--publication-store', type=Path, help=f'Published KB store (default: {DEFAULT_STORE})')
    parser.add_argument('--pid', type=int)
    parser.add_argument('--osd', action=argparse.BooleanOptionalAction, default=APPRAISAL.osd)
    parser.add_argument('--osd-seconds', type=positive_float, default=APPRAISAL.display_seconds)
    parser.add_argument(
        '--rune-marks',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.rune_marks,
        help='serve: HUD arrows to valuable runes on the ground (APPRAISAL.rune_minimum and up)',
    )
    parser.add_argument(
        '--hud-scene', type=Path, default=DEFAULT_SCENE, help='HUD scene directory (inventory_tracking/hud)'
    )
    parser.add_argument('--cache-seconds', type=positive_float, default=APPRAISAL.cache_seconds)
    requests = parser.add_mutually_exclusive_group()
    requests.add_argument('--collect', action='store_true', help='request: send a Win+S collection instead')
    requests.add_argument(
        '--equipped', action='store_true', help='request: record only worn character/mercenary items instead'
    )
    requests.add_argument(
        '--disagree', action='store_true', help='request: flag the displayed Alt+D verdict for review'
    )
    requests.add_argument('--shop', action='store_true', help='request: send a Win+D shop check instead')
    requests.add_argument(
        '--level',
        action='store_true',
        help='request: send Win+C instead (show the level map again and dump level memory)',
    )
    requests.add_argument('--macro', action='store_true', help='request: send Win+X instead (run or cancel the macro)')
    parser.add_argument('--level-output', type=Path, default=LEVEL_OUTPUT, help='Win+C level dump runs')
    parser.add_argument(
        '--level-evidence', type=Path, default=DEFAULT_EVIDENCE, help='evidence saved on each guided level entry'
    )
    parser.add_argument('--collection-database', type=Path, default=COLLECTION_DATABASE)
    parser.add_argument('--collection-output', type=Path, default=COLLECTION_OUTPUT)
    parser.add_argument('--collection-html', type=Path, default=COLLECTION_HTML, help='page regenerated after Win+S')
    parser.add_argument(
        '--shop-auto',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.shop_auto,
        help='serve: scan loaded vendor stock automatically when its first gear item changes',
    )
    parser.add_argument('--shop-poll-seconds', type=positive_float, default=APPRAISAL.shop_poll_interval)
    parser.add_argument(
        '--stash-auto',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.stash_auto,
        help='serve: run a Win+S collection automatically every time the stash panel is closed',
    )
    parser.add_argument('--stash-poll-seconds', type=positive_float, default=APPRAISAL.stash_poll_interval)
    parser.add_argument(
        '--identify-auto',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.identify_auto,
        help='serve: assess inventory and cube items the moment they become identified (Cain, scrolls)',
    )
    parser.add_argument(
        '--level-guide',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.level_guide,
        help='serve: on entering a guided level (levels/handlers/), show an arrow to its target for a few seconds',
    )
    parser.add_argument(
        '--terror-probe',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.terror_probe,
        help='serve: record monster sightings and kills to terror-probe.jsonl (Terror Zone research)',
    )
    parser.add_argument('--identify-poll-seconds', type=positive_float, default=APPRAISAL.identify_poll_interval)
    args = parser.parse_args(argv)
    if args.database is None and args.publication_store is None:
        args.publication_store = DEFAULT_STORE
    configure_logging()
    if args.command == 'serve':
        return serve(args)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.settimeout(0.25)
            prefix = (
                'disagree '
                if args.disagree
                else SHOP_PREFIX
                if args.shop
                else LEVEL_PREFIX
                if args.level
                else MACRO_PREFIX
                if args.macro
                else EQUIPMENT_PREFIX
                if args.equipped
                else REQUEST_PREFIX
                if args.collect
                else ''
            )
            message = f'{prefix}{time.monotonic()}'
            client.sendto(message.encode('ascii'), str(args.socket))
    except OSError:
        notify(
            'D2R appraisal worker is not running',
            'Start: uv run --offline -m inventory_tracking.appraisal.service serve',
        )
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
