"""Read the worker's short-lived display lease in a separate GTK process."""

import argparse
import json
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.common import LOG
from inventory_tracking.config import OSD, with_overrides
from inventory_tracking.presentation import StyledLine
from inventory_tracking.reports import publish


LEASE_SECONDS = 1.5


def publish_display(path, record):
    lines = []
    if record is not None:
        lines = [line.to_payload() for line in ItemAssessment.from_record(record).to_osd()]
    publish(path, {'checked_at': time.monotonic(), 'lines': lines})


def read_display(path, now):
    try:
        frame = json.loads(path.read_text())
        if not 0 <= now - frame['checked_at'] < LEASE_SECONDS:
            return []
        lines = frame['lines']
        if not isinstance(lines, list):
            return []
        return [line if isinstance(line, str) else StyledLine.from_payload(line) for line in lines]
    except OSError, ValueError, KeyError, TypeError:
        return []


@contextmanager
def overlay_process(directory, enabled):
    path = directory / 'osd.json'
    publish_display(path, None)
    if not enabled:
        yield None
        return
    with (directory / 'osd.log').open('a') as log:
        process = subprocess.Popen(
            [sys.executable, '-m', 'inventory_tracking.appraisal.overlay', str(path.resolve())],
            stdout=log,
            stderr=log,
        )
        try:
            yield path
        finally:
            publish_display(path, None)
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.returncode not in (0, -15):
                LOG.warning('Appraisal OSD exited with %s; see %s', process.returncode, directory / 'osd.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    from inventory_tracking.osd.window import show

    return show(
        lambda *, now: read_display(args.path, now),
        with_overrides(OSD, x=0, y=0),
        assessment=True,
    )


if __name__ == '__main__':
    raise SystemExit(main())
