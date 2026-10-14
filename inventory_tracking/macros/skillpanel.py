"""The right mouse skill put back by the macro in keyboard mode, in the game's skill selection, as a player does it:
a click on the right skill's button on the HUD opens the selection (the `skill_select` panel, read), a click on the
skill's icon there puts it on the right button and closes the panel. The right skill read after it is the evidence.

Why (rca/2026-10-14/run-1904-findings.md §3.7): in controller mode the client writes the pad's skills into the mouse
buttons' fields, and after a stint the right button held Summon Defiler (the pad's B) back in keyboard mode. Attack
mode by the keys needs the strike on the right button or a key; three runs stopped in 19.4 s until the player
selected it by hand (the player's ruling of 2026-10-14: the macro selects it itself).

Where (window fractions are not kept: the HUD is drawn to the window's height and centred, so a place is an offset
from the window's bottom centre in window heights, `Place`). The player's own selection at 22:09:50-51 on 2026-10-14
(take 20261014T190924Z-108, a 2560x1418 window): the panel opened with the pointer at (0.536, 0.978) of the window,
the right skill's button (RIGHT_BUTTON); the click that put Echoing Strike on the right button was at (0.669, 0.696).
An icon's place depends on the skills the character has (the panel's rows): it is the character's, given by its
build layer (`Build.skill_icons`, builds/characters.py). A skill with no place there is not selected.
"""

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.world import World


Place = tuple[float, float]  # (right of the window's centre, below its bottom edge), in window heights
RIGHT_BUTTON: Place = (0.0652, -0.0215)  # the right skill's button on the HUD (the module text)
PANEL = 'skill_select'  # native/layout.py PANEL_FLAGS
PANEL_WAIT = 0.6  # seconds for the panel to open after the click, and to close with the skill on the button after
SCATTER = (3, 2)  # pixels: an icon is about 60 wide on a 1418-high window


def window_point(place: Place, rect: tuple[int, int, int, int]) -> tuple[float, float]:
    """The window fraction of `place` in a window of `rect` (x, y, width, height)."""
    width, height = rect[2], rect[3]
    return 0.5 + place[0] * height / width, 1.0 + place[1]


def holds(world: World, skill: int) -> bool:
    return world.player is not None and world.player.right_skill == skill


def select_right(run: Run, skill: int, icon: Place) -> None:
    """Put `skill` on the right mouse button by the skill selection (the module text): the right skill's button
    clicked, the panel seen open, the skill's icon at `icon` clicked, the skill seen on the right button with the
    panel closed. Keyboard mode only (a click flips controller mode back). Abort, the panel closed again, when a step
    is not seen; nothing is clicked with another panel open (a click there is the panel's)."""
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
        run.actuator.click()  # the button again closes the selection: no click of the run's lands in it
    held = now.player.right_skill if now.player is not None else None
    raise Abort(
        f'the skill selection did not put {skill_name(skill)} on the right button (it holds {skill_name(held)}; '
        f'the icon looked for at {icon[0]:+.3f}, {icon[1]:+.3f} window heights from the bottom centre)'
    )
