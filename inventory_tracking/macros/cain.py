"""Deckard Cain's Identify Items: the KP_6 loop's free mass identify in Pandemonium Fortress
(routes/lower-kurast-loop-plan.md §15); the Tome (junk.py `identify`) is the fallback.

The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to loop".

The visit is the vendors' (shop.py): walk until he is drawn well inside the window, open his menu, click the
Identify Items line at each of `lifts` until the items turn identified; the lift that took is learned (shop.py
`learned`). A lift that opens his talk is closed and the next one tried.
"""

from collections.abc import Sequence

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.shop import (
    LINE,
    WALK_SECONDS,
    WALKING,
    _close,
    known,
    menu_line,
    serving,
    walk_until,
    whereabouts,
)


__all__ = ['CAIN', 'identify_all']

CAIN = 246  # monstats *hcIdx (`cain4`): Deckard Cain in Pandemonium Fortress
SEEN = (0.1, 0.9, 0.42, 0.8)  # window fractions he must be drawn within: his menu is drawn over him
IDENTIFIED_SECONDS = 1.5  # for the items' flags to turn after the click


def lifts() -> tuple[float, ...]:
    """Lifts over his drawn point to click Identify Items at: the learned one (shop.py `known`), then 0.16 up by
    half a line, nearest the learned one first."""
    scan = tuple(0.16 + step * LINE / 2 for step in range(12))
    learned_lift = known(CAIN)
    if learned_lift:
        # The line drifts a step or two with where he is drawn; scanning from 0.16 took 8.5 s (2026-10-17 17:05:56)
        scan = tuple(sorted(scan, key=lambda lift: abs(lift - learned_lift)))
    return tuple(dict.fromkeys(round(lift, 4) for lift in ((learned_lift,) if learned_lift else ()) + scan))


def identify_all(run: Run, unknown: Sequence[Carried]) -> int:
    """Identify the carried `unknown` items at Cain; returns how many turned identified. Mouse mode only. `Abort`,
    his windows closed, when he is not found or no line identified them."""
    if run.pad is not None:
        raise Abort('Cain needs mouse mode')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or run.carried is None:
        raise Abort('no game window, or the inventory is not read')
    if not unknown:
        return 0
    aspect = rect[2] / rect[3]
    units = {item.unit_id for item in unknown}

    def known_now() -> int:
        pack = run.reads.carried()
        if pack is None:
            return 0
        return sum(1 for item in (*pack.items, *pack.in_cube) if item.unit_id in units and item.identified)

    run.say(f'Cain: {len(unknown)} to identify')
    with serving(CAIN):

        def place(world: World) -> tuple[float, float] | None:
            return whereabouts(world)  # his usual place when out of the units' reach (shop.py USUAL)

        walk_until(run, place, SEEN, 'Deckard Cain')
        run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS)
        try:
            menu_line(
                run, aspect, 'Identify Items', lifts(),
                lambda _lift: run.seen(lambda _w: known_now() == len(units), IDENTIFIED_SECONDS) is not None,
            )  # fmt: skip
        finally:
            _close(run)
    done = known_now()
    LOG.info('Macro: Cain: %d of %d items identified', done, len(units))
    return done
