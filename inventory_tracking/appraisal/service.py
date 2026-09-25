"""Host Alt+D/Win+S worker. Start `serve`, then use the compositor's `request` bindings.

Datagrams: a bare monotonic timestamp requests an Alt+D appraisal; `collect <timestamp>`
requests a Win+S inventory collection (`request --collect`).
"""

import argparse
import fcntl
import os
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext, suppress
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from inventory_tracking.appraisal.cache import database_revision
from inventory_tracking.appraisal.capture import AppraisalCapture, game_focused
from inventory_tracking.appraisal.overlay import overlay_process, publish_display
from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.appraisal.published_backend import PublishedAppraisal
from inventory_tracking.appraisal.text import value_watch_lines
from inventory_tracking.appraisal.worker import AppraisalWorker
from inventory_tracking.collection.export import DEFAULT_HTML as COLLECTION_HTML
from inventory_tracking.collection.service import DEFAULT_OUTPUT as COLLECTION_OUTPUT, REQUEST_PREFIX, Collector
from inventory_tracking.collection.store import DEFAULT_DATABASE as COLLECTION_DATABASE
from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.config import APPRAISAL
from inventory_tracking.native.session import GameProcessUnavailable
from inventory_tracking.osd.__main__ import positive_float
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication import DEFAULT_STORE


def memory_evidence(observation, database):
    result = retrieve_draft(observation, database)
    result['decision'].update(
        reason='Memory snapshot with limited stat decoding; local evidence requires review.',
        next_step='Review observed stats and unresolved fields against the local appraisal evidence.',
    )
    return result


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


def dispatch(data: bytes, now: float, worker, collector) -> bool:
    """Route one datagram: `collect <t>` to the collector, a bare `<t>` to the Alt+D worker."""
    try:
        text = data.decode('ascii').strip()
        if text.startswith(REQUEST_PREFIX):
            return collector.request(float(text[len(REQUEST_PREFIX) :]), now)
        return worker.request(float(text), now)
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
    """Attach once D2R.exe exists; other attach failures still abort the service."""
    waiting = False
    while True:
        try:
            return connect()
        except GameProcessUnavailable as exc:
            if not waiting:
                report.update(state='waiting', reason=str(exc))
                publish(directory / 'report.json', report)
                print(f'Waiting for D2R.exe. Reports: {directory}', flush=True)
                LOG.info('Waiting for game process: %s', exc)
                waiting = True
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
                    connection = reader.connect(attachment)
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
                if backend:
                    loaded = backend.repository.load()
                    if loaded.runtime is None:
                        raise ValueError(
                            'Offline publication unavailable; run uv run --offline python -m '
                            'pricing.knowledge.publication. ' + '; '.join(loaded.issues)
                        )
                pid, images, capture = wait_for_game(connect, directory, report)
                print(f'Ready for Alt+D. Reports: {directory}', flush=True)
                source = AppraisalCapture(pid, images, capture, reconnect=connect)

                with (
                    overlay_process(directory, args.osd) as display_path,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='appraisal-kb') as pool,
                    ThreadPoolExecutor(max_workers=1, thread_name_prefix='collection') as collection_pool,
                ):
                    worker = AppraisalWorker(
                        source,
                        backend.retrieve if backend else lambda o: memory_evidence(o, args.database),
                        lambda record: publish_request(directory, record, notifications=not args.osd),
                        pool,
                        display=(lambda record: publish_display(display_path, record)) if display_path else None,
                        display_seconds=args.osd_seconds,
                        cache_seconds=args.cache_seconds,
                        cache_context=backend.cache_context if backend else lambda: database_revision(args.database),
                        request_scope=backend.request_scope if backend else nullcontext,
                    )
                    collector = Collector(
                        source,
                        args.collection_database,
                        args.collection_output,
                        collection_pool,
                        html=args.collection_html,
                        capture_lock=worker.capture_lock,
                        focused=game_focused,
                        notify=notify,
                    )
                    print(f'Ready for Alt+D and Win+S. Collection database: {args.collection_database}', flush=True)
                    try:
                        while True:
                            worker.tick()
                            try:
                                data = server.recv(256)
                            except TimeoutError:
                                continue
                            dispatch(data, time.monotonic(), worker, collector)
                    finally:
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
    parser.add_argument('--cache-seconds', type=positive_float, default=APPRAISAL.cache_seconds)
    parser.add_argument('--collect', action='store_true', help='request: send a Win+S collection instead')
    parser.add_argument('--collection-database', type=Path, default=COLLECTION_DATABASE)
    parser.add_argument('--collection-output', type=Path, default=COLLECTION_OUTPUT)
    parser.add_argument('--collection-html', type=Path, default=COLLECTION_HTML, help='page regenerated after Win+S')
    args = parser.parse_args(argv)
    if args.database is None and args.publication_store is None:
        args.publication_store = DEFAULT_STORE
    configure_logging()
    if args.command == 'serve':
        return serve(args)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.settimeout(0.25)
            message = f'{REQUEST_PREFIX if args.collect else ""}{time.monotonic()}'
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
