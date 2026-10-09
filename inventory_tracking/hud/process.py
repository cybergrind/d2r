"""Start the HUD canvas next to a producer, keep one canvas per scene, and build producer widgets."""

import fcntl
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.hud.ground import ground_payload
from inventory_tracking.hud.payloads import card_payload, guide_payload
from inventory_tracking.hud.scene import LEASE_SECONDS, Widget
from inventory_tracking.native.layout import UI_PANELS_RVA
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
    """The level guide's display lines: the styled rows in the 'guide' slot, its MapCard as a map-only
    guide widget in the 'map' slot (top centre, user 2026-10-04), and the card's marked dots as ground
    marks over the game view (hud/ground.py)."""
    rows = [line for line in lines if isinstance(line, StyledLine)]
    card = next((line for line in lines if isinstance(line, MapCard)), None)
    widgets = [Widget('guide', 'guide', 'guide', guide_payload(rows, None))] if rows else []
    if card is None:
        return widgets
    # 'ground' sorts before the cards, so the marks are drawn under them.
    marks = ground_payload(card)
    ground = [Widget('ground', 'ground', 'ground', marks)] if marks else []
    return ground + widgets + [Widget('map', 'guide', 'map', guide_payload([], card))]


def card_widgets(lines, widget_id='card') -> list[Widget]:
    """An assessment/shop/identify card's lines as a text widget in the 'assessment' slot (cards of
    different producers stack there)."""
    return [Widget(widget_id, 'text', 'assessment', card_payload(lines))] if lines else []


def loot_widgets(lines) -> list[Widget]:
    """Valuable ground runes as arrow rows (a guide card without a map) in the 'loot' slot."""
    return [Widget('runes', 'guide', 'loot', guide_payload(lines, None))] if lines else []


def terror_widgets(lines) -> list[Widget]:
    """The Terror Zone card (terror/tracker.py) as a text widget in the 'terror' slot."""
    return [Widget('terror', 'text', 'terror', card_payload(lines))] if lines else []


class PanelBeacon:
    """Tells the canvas where the game's open-panel flags are, so it can read them every frame and
    dim the HUD while the player reads items (hud/live.py OpenPanels). Republished well inside the
    lease; `source` is asked each time, so a restarted game is followed."""

    INTERVAL = LEASE_SECONDS / 3

    def __init__(self, source, publish):
        self.source, self.publish = source, publish
        self.last: float | None = None

    def poll(self, now: float) -> None:
        if self.last is not None and now - self.last < self.INTERVAL:
            return
        self.last = now
        address = self.source.images['candidate_base'] + UI_PANELS_RVA
        self.publish([Widget('panels', 'panels', 'panels', {'live': [self.source.pid, address]})])


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
