"""Shared timestamps, errors, file reading and logging conventions."""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


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


class HighlightHandler(RichHandler):
    """Highlight explicitly marked lines on the console without mutating records."""

    def render_message(self, record, message):
        styled = getattr(record, 'styled_message', None)
        if isinstance(styled, Text) and styled.plain == message:
            return styled.copy()
        text = Text(message)
        highlights = getattr(record, 'highlight_lines', ())
        styles = getattr(record, 'line_styles', {})
        offset = 0
        for line in message.splitlines(keepends=True):
            style = 'bright_yellow' if line.strip() in highlights else styles.get(line.strip())
            if style:
                text.stylize(style, offset, offset + len(line.rstrip('\r\n')))
            offset += len(line)
        return text


def configure_logging():
    console = Console(stderr=True)
    if console.is_terminal:
        handler = HighlightHandler(console=console, show_path=False, markup=False, log_time_format='%Y-%m-%d %H:%M:%S')
        logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[handler])
    else:
        # Preserve line-oriented diagnostics for pipes and host watcher tools.
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
