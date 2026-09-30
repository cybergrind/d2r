"""Start the HUD canvas next to a producer, keep one canvas per scene, and build producer widgets."""

import fcntl
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.hud.payloads import card_payload, guide_payload
from inventory_tracking.hud.scene import Widget
from inventory_tracking.osd.level_map import MapCard
from inventory_tracking.presentation import StyledLine


def acquire_instance(scene_dir: Path):
    """An open lock file while this process owns the scene's canvas, or None if another does."""
    scene_dir.mkdir(parents=True, exist_ok=True)
    handle = (scene_dir / 'canvas.lock').open('a')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def guide_widgets(lines) -> list[Widget]:
    """The level guide's display lines (styled rows + one MapCard) as the 'guide' slot widget."""
    if not lines:
        return []
    rows = [line for line in lines if isinstance(line, StyledLine)]
    card = next((line for line in lines if isinstance(line, MapCard)), None)
    return [Widget('guide', 'guide', 'guide', guide_payload(rows, card))]


def card_widgets(lines) -> list[Widget]:
    """An assessment/shop/identify card's lines as the 'assessment' slot text widget."""
    return [Widget('card', 'text', 'assessment', card_payload(lines))] if lines else []


def loot_widgets(lines) -> list[Widget]:
    """Valuable ground runes as arrow rows (a guide card without a map) in the 'loot' slot."""
    return [Widget('runes', 'guide', 'loot', guide_payload(lines, None))] if lines else []


@contextmanager
def hud_process(scene_dir: Path, enabled: bool, log: Path):
    """Run `python -m inventory_tracking.hud` for the producer's lifetime (it exits if one already runs)."""
    if not enabled:
        yield
        return
    with log.open('a') as stream:
        process = subprocess.Popen(
            [sys.executable, '-m', 'inventory_tracking.hud', '--scene', str(scene_dir)], stdout=stream, stderr=stream
        )
        try:
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.returncode not in (0, -15):
                LOG.warning('HUD canvas exited with %s; see %s', process.returncode, log)
