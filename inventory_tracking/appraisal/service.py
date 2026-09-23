"""Host Alt+D worker. Start `serve`, then use the compositor's `request` binding."""

import argparse
import fcntl
import os
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path

from inventory_tracking.appraisal.capture import AppraisalCapture
from inventory_tracking.appraisal.text import format_appraisal, roll_styles, unresolved_lines
from inventory_tracking.appraisal.worker import AppraisalWorker
from inventory_tracking.common import LOG, configure_logging, log_to_file, timestamp
from inventory_tracking.reports import create_run, publish
from inventory_tracking.tracking.reader import LiveReader
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.pipeline import retrieve_draft


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


def publish_request(directory, record):
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
        text = format_appraisal(record, frozen)
        (request_dir / 'appraisal.txt').write_text(text, encoding='utf-8')
        LOG.info('%s', text, extra={'highlight_lines': unresolved_lines(record), 'line_styles': roll_styles(record)})
    else:
        LOG.info('Appraisal request %s: %s', record['request_id'], record['state'])
    if record['state'] == 'complete':
        extraction = record['result']['extraction']
        item = extraction['item']
        stats = '; '.join(s['text'] for s in extraction.get('decoded_stats', [])[:4])
        if not stats:
            stats = '; '.join(a['label'].replace('{{value}}', str(a['value'])) for a in item['affixes'][:4])
        notify(
            f'{item["name"]} — review required',
            f'{stats or "No supported stats"}\nPrice unresolved. Report: {request_dir}',
        )
    elif record['state'] == 'rejected':
        detail = record['reason']
        if record.get('diagnostics_file'):
            detail += '\nPanel diagnostics saved for investigation.'
        notify('Appraisal unavailable', detail)


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
            server.settimeout(0.5)
            try:
                pid, images, capture = LiveReader(directory, pid=args.pid).connect(directory)
                report.update(state='ready', game_identity=images['identity'], socket=str(endpoint))
                publish(directory / 'report.json', report)
                print(f'Ready for Alt+D. Reports: {directory}', flush=True)
                source = AppraisalCapture(pid, images, capture)

                with ThreadPoolExecutor(max_workers=1, thread_name_prefix='appraisal-kb') as pool:
                    worker = AppraisalWorker(
                        source,
                        lambda o: memory_evidence(o, args.database),
                        lambda record: publish_request(directory, record),
                        pool,
                    )
                    try:
                        while True:
                            try:
                                data = server.recv(256)
                            except TimeoutError:
                                continue
                            try:
                                requested = float(data.decode('ascii'))
                            except ValueError, UnicodeError:
                                continue
                            worker.request(requested, time.monotonic())
                    finally:
                        with worker.lock:
                            worker.generation += 1
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
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--pid', type=int)
    args = parser.parse_args(argv)
    configure_logging()
    if args.command == 'serve':
        return serve(args)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.settimeout(0.25)
            client.sendto(str(time.monotonic()).encode('ascii'), str(args.socket))
    except OSError:
        notify(
            'D2R appraisal worker is not running',
            'Start: uv run --offline -m inventory_tracking.appraisal.service serve',
        )
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
