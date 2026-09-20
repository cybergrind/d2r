"""Shared timestamps, errors, file reading and logging conventions."""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


LOG = logging.getLogger('inventory_tracking')


def timestamp():
    return datetime.now(UTC).isoformat()


def error(exc):
    return {'error': str(exc), 'errno': getattr(exc, 'errno', None)}


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        return error(exc)


def configure_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


@contextmanager
def log_to_file(path):
    handler = logging.FileHandler(path, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOG.addHandler(handler)
    try:
        yield
    finally:
        handler.flush()
        LOG.removeHandler(handler)
        handler.close()
