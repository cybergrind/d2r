"""Atomic report publication and polling across the host/sandbox boundary."""

import json
import time

from .common import LOG


def publish(path, report):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(path)


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
