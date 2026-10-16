"""Host Alt+D/Win+S/Win+D/Win+C worker. Start `serve`, then use the compositor's `request` bindings.

Datagrams: a bare monotonic timestamp requests an Alt+D appraisal; `collect <timestamp>`
requests a Win+S inventory collection (`request --collect`: every container, mercenary
equipment and the character sheet); `equipped <timestamp>` (`request --equipped`, no
binding) records only what the character and the mercenary wear. `shop <timestamp>` requests
a Win+D shop check (`request --shop`). `level <timestamp>` (`request --level`, Win+C) shows
the level map card again (fresh position, any level; a double press pins or unpins it) and
dumps the current level's room/unit structures for research (runs/level/). `macro <timestamp>`
(`request --macro`, the macro request) runs the macro for where the character is, or cancels a running one
(inventory_tracking/macros/plan.md); `teleport <timestamp>` (`request --teleport`, the teleport step) takes one
step toward the level card's mark: a teleport as far as the screen allows, or a walk into a near
door (inventory_tracking/macros/teleport.py); `hunt elites <timestamp>` (`request --hunt-elites`,
the seek step) takes one step toward the nearest elite, else toward an unexplored room, and `hunt any
<timestamp>` (`request --hunt-any`, the attack mode toggle) toggles attack mode, which kills whatever comes into reach
while the player moves about (macros/hunt.py); `pickup <timestamp>` (`request --pickup`, the pickup step) picks up
a valuable drop or a potion the belt wants, else does a seek step (macros/pickup.py). The level card is
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
import math
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from functools import partial
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from inventory_tracking import builds
from inventory_tracking.appraisal.cache import database_revision
from inventory_tracking.appraisal.cadence import Mode, Schedule, cadences
from inventory_tracking.appraisal.capture import AppraisalCapture, RecentFocus
from inventory_tracking.appraisal.hotkeys import Hotkeys
from inventory_tracking.appraisal.load import LoadMeter
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
from inventory_tracking.builds.characters import PLAYS
from inventory_tracking.collection.export import DEFAULT_HTML as COLLECTION_HTML
from inventory_tracking.collection.service import (
    DEFAULT_OUTPUT as COLLECTION_OUTPUT,
    EQUIPMENT_PREFIX,
    REQUEST_PREFIX,
    Collector,
)
from inventory_tracking.collection.store import DEFAULT_DATABASE as COLLECTION_DATABASE
from inventory_tracking.collection.watch import StashWatcher
from inventory_tracking.combat import macro_state
from inventory_tracking.combat.record import CombatRecorder
from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.config import APPRAISAL, DCLONE, SHOW_ITEMS, TRADERIE
from inventory_tracking.hud.dclone import dclone_watch
from inventory_tracking.hud.process import (
    ModeBeacon,
    PanelBeacon,
    card_widgets,
    guide_widgets,
    hud_process,
    loot_widgets,
    terror_widgets,
)
from inventory_tracking.hud.scene import DEFAULT_SCENE, publish_layer
from inventory_tracking.hud.traderie import traderie_watch
from inventory_tracking.identify.service import IdentifyWorker
from inventory_tracking.input.compositor import hotkeys
from inventory_tracking.input.gamepad import PadKeys, bind_table, legend, read_settings
from inventory_tracking.levels.dump import (
    DEFAULT_OUTPUT as LEVEL_OUTPUT,
    REQUEST_PREFIX as LEVEL_PREFIX,
    LevelDumper,
)
from inventory_tracking.levels.evidence import DEFAULT_EVIDENCE, EvidenceLog
from inventory_tracking.levels.guide import LevelGuide
from inventory_tracking.levels.memory import observe_walkable, observe_waypoints
from inventory_tracking.levels.walls import WallLibrary
from inventory_tracking.loot.materials import material_classes
from inventory_tracking.loot.watch import RuneWatcher
from inventory_tracking.macros.card_goal import CardGoals
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.latency import FILE as LATENCY_FILE, Trace
from inventory_tracking.macros.pad import KeyRoute, PadPlay
from inventory_tracking.macros.pickup import wanted
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.runner import (
    HUNT_ANY,
    HUNT_ANY_PREFIX,
    HUNT_ELITES,
    HUNT_ELITES_PREFIX,
    LOOP,
    LOOP_PREFIX,
    PICKUP,
    PICKUP_PREFIX,
    REQUEST_PREFIX as MACRO_PREFIX,
    TELEPORT,
    TELEPORT_PREFIX,
    MacroRunner,
)
from inventory_tracking.macros.skills import NAMES as SKILL_NAMES
from inventory_tracking.macros.world import observe_things
from inventory_tracking.native.process import find_game_processes
from inventory_tracking.native.session import GameNotReady, GameProcessUnavailable
from inventory_tracking.osd.__main__ import positive_float
from inventory_tracking.reports import create_run, publish
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.shop.service import REQUEST_PREFIX as SHOP_PREFIX, ShopWorker, triage_stock
from inventory_tracking.terror.bosses import BossTracker
from inventory_tracking.terror.probe import TerrorProbe
from inventory_tracking.terror.shards import ShardWatch
from inventory_tracking.terror.tracker import ZoneTracker
from inventory_tracking.tracking.input_mode import InputModeWatch
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


@contextmanager
def publication_required():
    try:
        yield
    except ValueError as error:
        raise ValueError(f'{error}; run uv run --offline python -m pricing.knowledge.publication') from error


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


PAD_PREFIX = 'pad '  # request.py PREFIXES['pad']

# The macro's datagrams: handed to the runner the moment they are read (appraisal/hotkeys.py).
MACRO_ROUTINES = (
    (MACRO_PREFIX, None),
    (TELEPORT_PREFIX, TELEPORT),
    (HUNT_ELITES_PREFIX, HUNT_ELITES),
    (PICKUP_PREFIX, PICKUP),
    (HUNT_ANY_PREFIX, HUNT_ANY),
    (LOOP_PREFIX, LOOP),
)


def for_macro(data: bytes) -> bool:
    return data.startswith(tuple(prefix.encode('ascii') for prefix, _ in MACRO_ROUTINES))


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
    notes: dict[str, object] | None = None,
    pad=None,
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
        for prefix, routine in MACRO_ROUTINES:
            # The macro request (the macro for where the character is; a press while one runs cancels
            # it), the teleport, seek and pickup steps and the attack mode toggle (macros/runner.py).
            if text.startswith(prefix):
                stamp, *took = text[len(prefix) :].split()
                extra = dict(notes or {})
                if len(took) == 2:  # the request script's own start (request.py `startup`)
                    extra.update(spawn_ms=float(took[0]), spawn_cpu_ms=float(took[1]))
                if macro is None:
                    return False
                if routine is None:
                    return macro.request(float(stamp), now, **extra)
                return macro.request(float(stamp), now, routine, **extra)
        if text.startswith(PAD_PREFIX):  # the gamepad experiment (input/gamepad.py)
            return pad is not None and pad.request(APPRAISAL.gamepad_button, float(text[len(PAD_PREFIX) :]), now)
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


def bind_controller(args) -> None:
    """The played characters' controller bindings (config `gamepad_bindings`, input/gamepad.py
    `bind_table`; rca/2026-10-13/controller-mode.md section 3), written at the service's start and only while
    no D2R.exe runs: the client reads Saved Games once when it launches and writes the bindings back on
    leaving a game, so a write while it runs is never seen and is overwritten (loot-to-cube-mouse.md)."""
    if not APPRAISAL.gamepad_bind or not APPRAISAL.gamepad_bindings:
        return
    if find_game_processes():
        LOG.info('Controller bindings: D2R.exe runs, the files are left alone (close the game first)')
        return
    for name in PLAYS:
        try:
            lines = bind_table(
                SHOW_ITEMS.saved_games,
                name,
                APPRAISAL.gamepad_bindings,
                args.output.parent / 'gamepad',
                overwrite=APPRAISAL.gamepad_overwrite,
                names=SKILL_NAMES,
            )
        except OSError as exc:
            LOG.warning('Controller bindings: the file of %s was not written: %s', name, exc)
            continue
        for line in lines:
            LOG.info('Controller bindings: %s', line)


def controller_settings() -> None:
    """The two options that decide what reaches a controller record (input/gamepad.py `read_settings`;
    rca/2026-10-13/controller-gaps.md section 2): Quick Cast (a keyboard skill key casts its controller record in
    controller mode) and the separate bindings of the second weapon set. Read only, at the service's start."""
    try:
        found = read_settings(SHOW_ITEMS.saved_games)
    except (OSError, ValueError) as exc:
        LOG.info('Controller settings: Settings.json not read: %s', exc)
        return
    LOG.info(
        'Controller settings: %s (Settings.json; the game read it at its launch, the options menu may change it)',
        ', '.join(f'{name} {value if value is not None else "missing"}' for name, value in found.items()),
    )


def run_service(args, directory, report):
    # The GIL convoy (rca/2026-10-13/latency-findings.md 2.3): each pread of the game's memory gives the GIL up and
    # waits for it back up to this interval while another thread runs Python (config.py `switch_interval`).
    sys.setswitchinterval(APPRAISAL.switch_interval)
    controller_settings()
    bind_controller(args)
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
                recent = RecentObservations(stored_observations(args.output))
                with ExitStack() as starting:
                    # Under the lock, so a second worker that is refused never clears the first one's binds.
                    starting.enter_context(hotkeys())
                    # The canvas and the Traderie watch run from the start: notifications are
                    # shown while this process still waits for the game.
                    starting.enter_context(hud_process(args.hud_scene, args.osd, directory / 'hud.log'))
                    starting.enter_context(
                        traderie_watch(args.hud_scene, args.osd and args.traderie, directory / 'traderie.log')
                    )
                    starting.enter_context(dclone_watch(args.hud_scene, args.osd and args.dclone))
                    # Loading the KB and the first lookups take seconds in each lookup process, so
                    # they start first and warm up while this process loads the KB and finds the game.
                    warm, startup_generation = (), None
                    if backend:
                        with publication_required():
                            startup_generation = backend.pointer()
                        warm = (warm_publication, (args.publication_store, startup_generation))
                    # Separate processes: KB lookups would otherwise hold this process's GIL and stall the loop.
                    appraisal_lookups = starting.enter_context(RetrievalProcess(*warm))
                    identify_lookups = starting.enter_context(
                        RetrievalGroup(APPRAISAL.identify_lookup_processes, triage_warm, (recent.next(),))
                    )
                    if backend:
                        with publication_required():
                            backend.start(startup_generation)
                    starting.enter_context(refreshing(backend, [appraisal_lookups], args.publication_store))
                    # Detail warm-up can take seconds. Unrouted identify items use this
                    # already-warm process rather than blocking the fast worker queues.
                    starting.enter_context(
                        KeepWarm(
                            [appraisal_lookups],
                            warm_lookup(backend, args.database, recent),
                            interval=APPRAISAL.retrieval_keep_warm_interval,
                        )
                    )
                    starting.enter_context(
                        KeepWarm(
                            identify_lookups.processes,
                            warm_identify_lookup(recent),
                            interval=APPRAISAL.retrieval_keep_warm_interval,
                        )
                    )
                    pid, images, capture = wait_for_game(connect, directory, report)
                    lookups = starting.pop_all()
                print(f'Ready for Alt+D. Reports: {directory}', flush=True)
                source = AppraisalCapture(pid, images, capture, reconnect=connect)

                with (
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='appraisal-kb') as pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='collection') as collection_pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='shop') as shop_pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='identify') as identify_pool,
                    ThreadPoolExecutor(
                        max_workers=APPRAISAL.identify_lookup_processes, thread_name_prefix='identify-lookup'
                    ) as identify_lookup_pool,
                    lookups,  # the canvas, the lookup processes and their warmers, started above
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
                        gambling=lambda: shop.stock_state == 'gamble',
                    )
                    level = LevelDumper(source, args.level_output, capture_lock=worker.capture_lock, notify=notify)

                    def display_macro(lines):
                        if args.osd:
                            publish_layer(args.hud_scene, 'macro', card_widgets(lines, 'macro'))

                    played = builds.pursuing if APPRAISAL.macro_pursuit else (lambda build: build)
                    macro = MacroRunner(
                        source,
                        capture_lock=worker.capture_lock,
                        saved_games=SHOW_ITEMS.saved_games,
                        display=display_macro,
                        trace=Trace(directory / LATENCY_FILE),
                        # The builds a run is played by: handed in here, the framework imports none
                        builds=tuple(map(played, builds.BUILDS)),
                        fallback=played(builds.FALLBACK),
                        loop_items=args.output / 'loop-items.json',
                    )
                    # Per-game monster/Herald state: the Terror card and the level map shading.
                    zones = ZoneTracker(args.output / 'terror-games.json') if args.terror_probe else None
                    map_dots = partial(zones.map_dots, danger=APPRAISAL.danger_marks) if zones is not None else None
                    # The routes (levels/routes.md): the stage each level is at in this game. The level
                    # card leads with its mark and the teleport key performs it; the monster tracker
                    # says which bosses are dead (without it a fight is not a stage the key performs).
                    progress = Progress(
                        ROUTES,
                        PERFORMED,
                        zones.killed if zones is not None else None,
                        zones.terrorized if zones is not None else None,
                    )
                    macro.progress = progress
                    if args.level_guide:
                        guide = LevelGuide(
                            source,
                            capture_lock=worker.capture_lock,
                            focused=focused,
                            display=lambda lines: publish_layer(args.hud_scene, 'levels', guide_widgets(lines)),
                            seconds=APPRAISAL.level_guide_seconds,
                            poll_interval=APPRAISAL.level_guide_poll_interval,
                            evidence=EvidenceLog(args.level_evidence).save,
                            # unchanged rooms are not converted again (levels/memory.py `walkable_tiles`)
                            observe_walls=partial(observe_walkable, cache={}) if APPRAISAL.level_walls else None,
                            library=WallLibrary() if APPRAISAL.level_walls else None,
                            visited_rooms=zones.visited_rooms if zones is not None else None,
                            map_dots=map_dots,
                            on_rooms=zones.level_layout if zones is not None else None,
                            observe_waypoints=observe_waypoints,
                            pinned=APPRAISAL.level_guide_pinned,
                            lead=progress.lead,
                            # The first row and arrow: the route's goal, the macro's own (macros/card_goal.py).
                            goals=CardGoals(
                                progress,
                                hostiles=zones.hostiles if zones is not None else None,
                                remembered=zones.remembered if zones is not None else None,
                                supers=zones.supers if zones is not None else None,
                            ),
                            observe_things=observe_things,
                        )
                        macro.target = guide.target  # the teleport step moves toward the card's first mark
                        macro.marks = guide.marks
                        # The seek step and attack mode: the level's rooms and walls, remembered elites, explored rooms.
                        macro.supers = zones.supers if zones is not None else None
                        macro.hunter = Hunter(
                            guide.level,
                            zones.remembered if zones is not None else None,
                            zones.visited_rooms if zones is not None else None,
                            build=builds.FALLBACK,  # until a run has seen the character (runner.py `choosing`)
                        )
                    combat = None
                    if args.combat_record:
                        combat = CombatRecorder(
                            source,
                            capture_lock=worker.capture_lock,
                            output=args.output.parent / 'combat',
                            areas=None if APPRAISAL.combat_everywhere else frozenset(APPRAISAL.combat_areas),
                            keep=int(APPRAISAL.combat_keep_gb * 1024**3),
                            rate=APPRAISAL.combat_rate,
                            level=guide.level if guide is not None else None,
                            macro_working=lambda: macro.working,
                            paths=args.combat_paths,
                            town=APPRAISAL.combat_town,
                            loot=lambda memory: memory.loot(**wanted()),
                            macro_state=lambda: macro_state.snapshot(macro),
                            code=macro_state.version(),
                        )
                        macro.noted = combat.recorder.note
                        macro.trace.noted = combat.recorder.note
                        combat.recorder.routine = lambda: macro.routine  # a `sent` input's routine (record.py)
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
                            unique_minimum=APPRAISAL.unique_minimum if APPRAISAL.unique_marks else None,
                            materials=material_classes(APPRAISAL.material_marks),
                            left=macro.put_down.at,  # what the player put down this game: no arrow to it
                        )
                    terror = None
                    if args.terror_probe:
                        terror = TerrorProbe(
                            source,
                            directory / 'terror-probe.jsonl',
                            capture_lock=worker.capture_lock,
                            poll_interval=APPRAISAL.terror_probe_interval,
                            summary_seconds=APPRAISAL.terror_summary_seconds,
                            around_seconds=APPRAISAL.terror_around_seconds,
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
                            shards=ShardWatch(terrorized=zones.terrorized) if zones is not None else None,
                        )
                    stash = None
                    if args.stash_auto:
                        stash = StashWatcher(
                            lambda: observe_panels(source.pid, source.images),
                            lambda now: collector.request(now, now, trigger='stash-closed'),
                            poll_interval=args.stash_poll_seconds,
                        )
                    panel_beacon = (
                        PanelBeacon(source, lambda widgets: publish_layer(args.hud_scene, 'panels', widgets))
                        if args.osd
                        else None
                    )
                    # The game's input mode (tracking/input_mode.py; rca/2026-10-13/controller-mode.md): read on
                    # its own thread, each flip logged with its time and given to the combat take.
                    pad = PadKeys() if APPRAISAL.gamepad_button or APPRAISAL.controller_play else None
                    input_watch = InputModeWatch(
                        source,
                        rate=APPRAISAL.input_mode_rate,
                        pressed=lambda: pad.pressed_at if pad is not None else None,
                        noted=combat.recorder.note if combat is not None else (lambda kind, **fields: None),
                        names=lambda skills: legend(skills, SKILL_NAMES, upto=28),  # 0-11, 12-15 by key, 16-27
                    )
                    if combat is not None:
                        combat.input_mode = lambda: input_watch.current.name if input_watch.current else None

                    def pad_legend():
                        skills = input_watch.bindings
                        if not skills:
                            return ()
                        # Records 12-15 (keyboard keys) once this session's `Pad key:` probe opened their route.
                        keyed = macro.pad_play is not None and macro.pad_play.route.open
                        return tuple(
                            line
                            for line in (
                                legend(skills[:6], SKILL_NAMES),
                                legend((-1,) * 6 + skills[6:12], SKILL_NAMES),
                                legend((-1,) * 12 + skills[12:16], SKILL_NAMES, upto=16) if keyed else '',
                            )
                            if line
                        )

                    mode_beacon = (
                        ModeBeacon(
                            lambda: (progress.game is not None, macro.attack_mode),
                            lambda widgets: publish_layer(args.hud_scene, 'mode', widgets),
                            input_mode=lambda: input_watch.current,
                            legend=pad_legend,
                            run_mode=lambda: macro.run_badge,  # 'CLEAR' / 'CLEAR TZ' for a full clear (runmode.py)
                        )
                        if args.osd
                        else None
                    )
                    watching = 'watching vendor stock' if args.shop_auto else 'no automatic shop watch'
                    stash_note = 'collecting on stash close' if stash else 'no stash watch'
                    identify_note = 'assessing on identify' if args.identify_auto else 'no identify watch'
                    print(
                        f'Ready for Alt+D, Win+S, Win+D and Win+C ({watching}; {stash_note}; {identify_note}). '
                        f'Collection database: {args.collection_database}',
                        flush=True,
                    )
                    # The slow work's pace by what the character and the macro do (appraisal/cadence.py), and the
                    # load measured once a second into the combat take (appraisal/load.py).
                    schedule = Schedule(
                        cadences(
                            shop=args.shop_poll_seconds,
                            identify=args.identify_poll_seconds,
                            stash=args.stash_poll_seconds,
                            runes=APPRAISAL.rune_poll_interval,
                            terror=APPRAISAL.terror_probe_interval,
                        ),
                        working=lambda: macro.working or macro.attack_mode,
                        area=lambda: macro.journey.area,
                    )
                    LOG.info(
                        'Service cadence (town / level / macro working): %s; switch interval %g s',
                        schedule.describe(),
                        sys.getswitchinterval(),
                    )
                    meter = LoadMeter(combat.recorder.note if combat is not None else (lambda kind, **fields: None))
                    macro.looked = meter.looked
                    timer = PassTimer(APPRAISAL.slow_loop_seconds, passed=meter.passed)

                    def macro_key(data, received):
                        step, since = timer.current
                        notes = {'pass': step, 'pass_ms': round(1000 * (received - since), 1)} if step else None
                        dispatch(data, received, worker, collector, macro=macro, notes=notes)

                    keys = Hotkeys(server, for_macro, macro_key)
                    if pad is not None:
                        pad.start()

                    def level_now():
                        if guide is not None:
                            guide.last_poll = -math.inf  # its next poll reads, whatever its interval
                        keys.wake()

                    macro.hurry = level_now
                    # The macros in controller mode (macros/pad.py): the hotkey's pad, made at its first need, and
                    # the mode, the controller's target and the bindings as the watch reads them.
                    macro.pad_play = PadPlay(
                        device=pad.device if pad is not None else (lambda: None),
                        mode=lambda: input_watch.current,
                        controller=lambda: input_watch.controller,
                        bindings=lambda: input_watch.bindings,
                        enabled=APPRAISAL.controller_play,
                        route=KeyRoute(enabled=APPRAISAL.controller_key_route),
                    )
                    keys.start()
                    try:
                        while True:
                            mode = schedule.update()
                            with timer.step('appraisal'):
                                worker.tick()
                            with timer.step('shop'):
                                shop.tick()
                                if schedule.paced('shop', shop):
                                    shop.poll(time.monotonic())
                            with timer.step('identify'):
                                identify.tick()
                                if schedule.paced('identify', identify):
                                    identify.poll(time.monotonic())
                            if stash is not None and schedule.paced('stash', stash):
                                with timer.step('stash'):
                                    stash.poll(time.monotonic())
                            if guide is not None:
                                with timer.step('level map'):
                                    guide.refresh_interval = schedule.seconds('level map') or 0.0
                                    guide.tick()
                                    guide.poll(time.monotonic())
                            if runes is not None:
                                with timer.step('runes'):
                                    runes.tick()
                                    if schedule.paced('runes', runes):
                                        runes.poll(time.monotonic())
                            if terror is not None:
                                with timer.step('terror probe'):
                                    if schedule.paced('terror probe', terror):
                                        terror.poll(time.monotonic())
                                    terror.tick()
                            with timer.step('macro'):
                                macro.poll(time.monotonic())
                            if combat is not None:
                                combat.poll(time.monotonic())
                            if panel_beacon is not None:
                                panel_beacon.poll(time.monotonic())
                            input_watch.poll(time.monotonic())
                            if mode_beacon is not None:
                                mode_beacon.poll(time.monotonic())
                            meter.poll(time.monotonic(), mode, noting=mode is not Mode.TOWN)
                            data = keys.get(APPRAISAL.poll_interval)
                            if data:  # not a wake (`Hotkeys.wake`)
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
                                        pad=pad,
                                    )
                            timer.finish()
                    finally:
                        keys.close()
                        macro.close()
                        if pad is not None:
                            pad.close()
                        input_watch.close()
                        if combat is not None:
                            combat.close()
                        shop.dismiss()
                        identify.dismiss()
                        if guide is not None:
                            guide.dismiss()
                        for producer in (
                            'appraisal',
                            'cards',
                            'identify',
                            'levels',
                            'loot',
                            'macro',
                            'panels',
                            'terror',
                        ):
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
        '--traderie',
        action=argparse.BooleanOptionalAction,
        default=TRADERIE.enabled,
        help='serve: HUD card for unread Traderie notifications, read through the browser (hud/traderie.py)',
    )
    parser.add_argument(
        '--dclone',
        action=argparse.BooleanOptionalAction,
        default=DCLONE.enabled,
        help='serve: HUD card for regions where Uber Diablo is close to walking (hud/dclone.py)',
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
    requests.add_argument(
        '--macro', action='store_true', help='request: the macro request instead (run or cancel the macro)'
    )
    requests.add_argument(
        '--teleport',
        action='store_true',
        help='request: the teleport step instead (one step toward the level map mark)',
    )
    requests.add_argument(
        '--hunt-elites', action='store_true', help='request: the seek step instead (one step toward the nearest elite)'
    )
    requests.add_argument('--hunt-any', action='store_true', help='request: the attack mode toggle instead')
    requests.add_argument(
        '--pickup',
        action='store_true',
        help='request: the pickup step instead (pick up a valuable or a potion, else a seek step)',
    )
    parser.add_argument('--level-output', type=Path, default=LEVEL_OUTPUT, help='Win+C level dump runs')
    parser.add_argument(
        '--combat-paths',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.combat_paths,
        help="serve: also write the monsters' path records to the takes (paths.jsonl; movement research)",
    )
    parser.add_argument(
        '--combat-record',
        action=argparse.BooleanOptionalAction,
        default=APPRAISAL.combat_record,
        help='serve: record takes of play in the configured levels under runs/combat (combat/record.py)',
    )
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
                else TELEPORT_PREFIX
                if args.teleport
                else HUNT_ELITES_PREFIX
                if args.hunt_elites
                else HUNT_ANY_PREFIX
                if args.hunt_any
                else PICKUP_PREFIX
                if args.pickup
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
