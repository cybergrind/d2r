"""Deckard Cain's Identify Items: the KP_6 loop's mass identify in Pandemonium Fortress
(routes/lower-kurast-loop-plan.md §15).

The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to loop";
"every class specific item can roll 35k". One click at Cain identifies every item carried, the cube's too, for no gold;
the Tome of Identify takes two clicks an item (macros/junk.py `identify`, kept as the fallback).

Cain stands in Pandemonium Fortress (monstats *hcIdx 246, `cain4`; the takes of 2026-10-17 put him at (5023, 5033),
27 units west of where a game starts). The visit is the vendors' (macros/shop.py): walked to until drawn well inside
the window, his menu opened by a click on him (`_open_menu`, `serving`), then his Identify Items line clicked at each
of `lifts` until the carried items' flags turn identified; the lift that took is learned (shop.py `learned`), as his
menu's lines are not measured. A line that opens his talk instead is closed (`_close`) and the next lift tried.
"""

from collections.abc import Sequence

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.shop import (
    LINE,
    WALK_SECONDS,
    WALKING,
    _close,
    _note,
    _open_menu,
    known,
    learned,
    serving,
    walk_until,
    whereabouts,
)
from inventory_tracking.macros.world import Carried, World


__all__ = ['CAIN', 'identify_all']

CAIN = 246  # monstats *hcIdx (`cain4`): Deckard Cain in Pandemonium Fortress (the takes of 2026-10-17)
SEEN = (0.1, 0.9, 0.42, 0.8)  # window fractions he is walked to be drawn within: his menu is drawn over him
IDENTIFIED_SECONDS = 1.5  # for the items' flags to turn after the click


def lifts() -> tuple[float, ...]:
    """The lifts over his drawn point (as his menu opened) the Identify Items line is clicked at: the learned one, then
    those from 0.16 up by half a line (LINE), the nearest it first."""
    scan = tuple(0.16 + step * LINE / 2 for step in range(12))
    learned_lift = known(CAIN)
    if learned_lift:
        # Nearest the learned one first: it drifts with where he is drawn, a step or two either way; from 0.16 up it
        # took four tries, 8.5 s, with the learned one two steps off (17:05:56-17:06:03 on 2026-10-17)
        scan = tuple(sorted(scan, key=lambda lift: abs(lift - learned_lift)))
    return tuple(dict.fromkeys(round(lift, 4) for lift in ((learned_lift,) if learned_lift else ()) + scan))


def identify_all(run: Run, unknown: Sequence[Carried]) -> int:
    """Cain's Identify Items for the carried `unknown` items (the module text); how many turned identified. Mouse mode
    only. `Abort` with his windows closed when he is not found or no line identified them."""
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
        pack = run.carried() if run.carried is not None else None
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
            for lift in lifts():
                drawn = _open_menu(run, aspect)
                run.actuator.move(drawn[0], drawn[1] - lift, scatter=(6, 1))
                _note(run, aspect, f'the Identify Items line clicked {lift:.4f} over him')
                run.actuator.click()
                if run.seen(lambda _w: known_now() == len(units), IDENTIFIED_SECONDS) is not None:
                    learned(CAIN, lift)
                    break
                _close(run)
            else:
                raise Abort("Cain's Identify Items line did not take at any line tried")
        finally:
            _close(run)
    done = known_now()
    LOG.info('Macro: Cain: %d of %d items identified', done, len(units))
    return done
