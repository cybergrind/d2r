"""Put a skill back on the right mouse button in keyboard mode through the game's skill selection panel: a click on
the HUD's right skill button opens it, a click on the skill's icon sets the skill and closes it.

Why: controller mode leaves the pad's skills on the mouse buttons (rca/2026-10-14/run-1904-findings.md §3.7); the
player's ruling of 2026-10-14: the macro selects it itself.

Places are offsets from the window's bottom centre in window heights (`Place`): the HUD scales with the window's
height. Icon places are the character's (`Build.skill_icons`, builds/characters.py); a skill with none is not
selected. Measured from take 20261014T190924Z-108.
"""

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import skill_name


Place = tuple[float, float]  # (right of the window's centre, below its bottom edge), in window heights
RIGHT_BUTTON: Place = (0.0652, -0.0215)  # the right skill's button on the HUD
PANEL = 'skill_select'  # native/layout.py PANEL_FLAGS
PANEL_WAIT = 0.6  # seconds for the panel to open, and to close after the icon click
SCATTER = (3, 2)  # pixels: an icon is about 60 wide on a 1418-high window


def window_point(place: Place, rect: tuple[int, int, int, int]) -> tuple[float, float]:
    """The window fraction of `place` in a window of `rect` (x, y, width, height)."""
    width, height = rect[2], rect[3]
    return 0.5 + place[0] * height / width, 1.0 + place[1]


def holds(world: World, skill: int) -> bool:
    return world.player is not None and world.player.right_skill == skill


def select_right(run: Run, skill: int, icon: Place) -> None:
    """Put `skill` on the right button via the skill selection, each step seen. Keyboard mode only (a click flips
    controller mode back); never over another open panel. Abort, the panel closed again, when a step is not seen."""
    if run.pad is not None:
        raise Abort('the skill selection takes the mouse: not in controller mode')
    world = run.world()
    if world.player is None:
        raise Abort('not in a game')
    was = world.player.right_skill
    if world.open_panels:
        raise Abort(f'{", ".join(world.open_panels)} open: the skill selection is not opened over it')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    began = run.clock()
    run.actuator.aim(*window_point(RIGHT_BUTTON, rect), scatter=SCATTER)
    run.actuator.click()
    if run.seen(lambda w: PANEL in w.open_panels, PANEL_WAIT) is None:
        raise Abort(f'the skill selection did not open {PANEL_WAIT:g}s after a click on the right skill button')
    run.actuator.aim(*window_point(icon, rect), scatter=SCATTER)
    run.actuator.click()
    done = run.seen(lambda w: holds(w, skill) and PANEL not in w.open_panels, PANEL_WAIT)
    if done is not None:
        LOG.info(
            'Macro: skill panel: %s put on the right button (it held %s), %.2fs',
            skill_name(skill), skill_name(was), run.clock() - began,
        )  # fmt: skip
        return
    now = run.world()
    if PANEL in now.open_panels:
        run.actuator.aim(*window_point(RIGHT_BUTTON, rect), scatter=SCATTER)
        run.actuator.click()  # closes the selection
    held = now.player.right_skill if now.player is not None else None
    raise Abort(
        f'the skill selection did not put {skill_name(skill)} on the right button (it holds {skill_name(held)}; '
        f'the icon looked for at {icon[0]:+.3f}, {icon[1]:+.3f} window heights from the bottom centre)'
    )
