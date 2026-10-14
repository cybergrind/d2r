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
from inventory_tracking.native.layout import CONTROLLER_MODE_RVA, UI_PANELS_RVA
from inventory_tracking.osd.level_map import MapCard
from inventory_tracking.presentation import StyledLine, Tone


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
        base = self.source.images['candidate_base']
        # The input mode byte too: the canvas lays its slots out for the controller layout while it is 1
        # (HUD.controller_slots, rca/2026-10-13/controller-mode.md section 5).
        payload = {'live': [self.source.pid, base + UI_PANELS_RVA], 'controller': base + CONTROLLER_MODE_RVA}
        self.publish([Widget('panels', 'panels', 'panels', payload)])


def terse_input(mode) -> str | None:
    """The game's input mode in a word for the mode line: 'kbd', 'pad', or the flip under way ('→pad')."""
    if mode is None:
        return None
    if mode.pending and mode.wanted is not None and mode.wanted != mode.controller:
        return '→pad' if mode.wanted else '→kbd'
    return 'pad' if mode.controller else 'kbd'


class ModeBeacon:
    """Says on the HUD whether the macro's attack mode is on (user, 2026-10-13: "we need to see some
    indicator when auto-attack is enabled or not on overlay"; the pickup key turns the mode on, and the
    attack key then turned it off unseen), the pickup key's run mode when it is a full clear (macros/runmode.py
    `badge`: 'CLEAR', 'CLEAR TZ'), and the game's input mode beside it: keyboard, controller, or a flip under
    way (rca/2026-10-13/controller-mode.md); in controller mode, which pad button casts what. Terse words, no
    sentences (the player, 2026-10-14). Republished well inside the lease, and at once when anything shown
    changes; nothing is shown out of a game. `state()` gives (in a game, attack mode on); `run_mode()` the run
    mode's word or None; `input_mode()` a tracking/input_mode.py InputMode or None (unread); `legend()` the
    bindings the game loaded, as lines ('Y Echoing Strike, ...'), or ()."""

    INTERVAL = LEASE_SECONDS / 3

    def __init__(self, state, publish, input_mode=lambda: None, legend=lambda: (), run_mode=lambda: None):
        self.state, self.publish, self.input_mode, self.legend = state, publish, input_mode, legend
        self.run_mode = run_mode
        self.last: float | None = None
        self.shown: tuple | None = None

    def poll(self, now: float) -> None:
        mode = self.input_mode()
        legend = tuple(self.legend()) if mode is not None and mode.controller else ()
        found = (*self.state(), self.run_mode(), terse_input(mode), legend)
        if found == self.shown and self.last is not None and now - self.last < self.INTERVAL:
            return
        self.last, self.shown = now, found
        in_game, on, run, label, legend = found
        if not in_game:
            self.publish([])
            return
        text = ' · '.join(part for part in ('ATTACK ON' if on else 'attack off', run, label) if part)
        lines = [StyledLine(text, Tone.SET if on else Tone.METADATA)]
        lines += [StyledLine(line, Tone.METADATA) for line in legend]
        self.publish([Widget('mode', 'text', 'mode', card_payload(lines))])


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
