"""Atomic report publication and polling across the host/sandbox boundary."""

import json
import os
import platform
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG, timestamp


def publish(path, report):
    # A temp file of the writer's own: two threads writing one card 2 ms apart shared `<name>.tmp`, the second
    # `replace` raised FileNotFoundError and killed the loop's thread (rca/2026-10-23/loop-no-legs.md, 00:41:44)
    temporary = path.with_name(f'{path.stem}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp')
    try:
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def watch(args):
    deadline = time.monotonic() + args.timeout
    seen = set() if args.include_existing else {p.parent.name for p in args.output.glob('*/report.json')}
    announced = set()
    LOG.info(
        'Watching %s for %ss; existing runs %s',
        args.output,
        args.timeout,
        'included' if args.include_existing else 'ignored',
    )
    while time.monotonic() < deadline:
        for path in sorted(args.output.glob('*/report.json'), reverse=True):
            if path.parent.name in seen:
                continue
            try:
                report = json.loads(path.read_text())
            except OSError, ValueError:
                continue
            if path.parent.name not in announced:
                LOG.info('Detected run %s: %s', path.parent.name, report.get('state'))
                announced.add(path.parent.name)
            if report.get('state') in {'complete', 'blocked', 'failed'}:
                print(path.read_text(), flush=True)
                LOG.info('Log file: %s', path.parent / 'probe.log')
                return report.get('exit_code', 1)
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    LOG.warning('Timed out waiting for a completed run; no new completion confirmed')
    return 124


def create_run(output: Path) -> tuple[Path, dict[str, Any]]:
    run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    directory = output / run_id
    directory.mkdir(parents=True)
    report = {
        'schema_version': 1,
        'run_id': run_id,
        'started_at': timestamp(),
        'state': 'running',
        'log': 'probe.log',
        'host': platform.node(),
        'reader_pid': os.getpid(),
    }
    return directory, report
