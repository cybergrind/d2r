"""One interaction with the game's UI: look whether its effect is there already, act, wait for the effect, try again a
bounded number of times, and fail by type (rca/2026-10-18/arch-actions.md §3 Option 1, steps 1 and 2).

Each module waited for its own effects in its own loop, and none looked before acting: seven incidents from
2026-10-16 to 2026-10-18 (Jamella's menu, the waypoint's panel, the stash, Halbu's menu, Save and Exit) were a click
made on an effect an earlier click had already brought, each fixed where it surfaced (the study's §2 A). Here:

- `until`: the first look in which a predicate holds within some seconds, or None. Every look goes through the run (a
  cancelled run stops at the next look, as `Run.world` does), and a world that cannot be read stops as `Run.world`
  stops (`Abort`), not as "not seen".
- `perform`: an `Action` done once: nothing pressed when its effect holds already (looked for `grace` seconds first),
  each try waited for, a repair between tries (`between`), a late effect accepted (`late`), one log line per action
  (`Macro: act <name>: …`), and `Failed` with the panels open when it never comes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import overload

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.engine import Run


__all__ = ['NOT_DONE', 'Action', 'Failed', 'Outcome', 'perform', 'until']

POLL = 0.05  # seconds between looks (the stash's and the cube's item waits looked this often)
NOT_DONE = 'not done'  # `Failed.reason`: no try brought the effect


class Failed(Abort):
    """An action whose effect did not come. Callers tell it by type and `reason`, never by its text; the text names the
    panels open at the end: the aims' "not under the pointer at any aim" did not, and a waypoint panel already open was
    read as the character's figure covering the aims (2026-10-17, the step back: the study's §2 A)."""

    def __init__(self, action: str, reason: str, world: World | None) -> None:
        panels = ', '.join(world.open_panels) if world is not None and world.open_panels else 'none'
        super().__init__(f'{action}: {reason} (open panels: {panels})')
        self.action = action
        self.reason = reason
        self.world = world


@dataclass(frozen=True)
class Action:
    """What `perform` does: `act` (given the try's number from 0) until `done` holds of a look at the game."""

    name: str  # for the log line and the failure: 'the stash', 'the cube open'
    done: Callable[[World], bool]  # the effect; also looked for before the first try
    act: Callable[[Run, int], None]  # one try
    wait: float  # seconds for `done` after a try
    tries: int = 1
    grace: float = 0.0  # seconds `done` is looked for before the first try (an earlier click's effect still coming)
    between: Callable[[Run, World], None] | None = None  # put right before the next try (stand, close, step back)
    late: float = 0.0  # seconds `done` is still looked for after the last try's wait


@dataclass(frozen=True)
class Outcome:
    already: bool  # the effect held before any try: nothing was pressed
    tries: int
    seconds: float


@overload
def until(run: Run, holds: Callable[[World], bool], seconds: float, *, poll: float = POLL) -> World | None: ...


@overload
def until[T](
    run: Run, holds: Callable[[T], bool], seconds: float, *, read: Callable[[], T | None], poll: float = POLL
) -> T | None: ...


def until(run, holds, seconds, *, read=None, poll=POLL):
    """The first look (`run.world()`, or `read()`: a None from it is no look) in which `holds`, within `seconds`;
    None when none comes. Looked at once first, so 0 seconds is one look. `Cancelled` at the first look after the run
    was cancelled."""
    deadline = run.clock() + seconds
    while True:
        if run.cancelled.is_set():
            raise Cancelled
        seen = run.world() if read is None else read()
        if seen is not None and holds(seen):
            return seen
        if run.clock() >= deadline:
            return None
        run.pace.sleep(poll)


def perform(run: Run, action: Action) -> Outcome:
    """Do `action` (the module text); how it went. `Failed` when no try brought its effect."""
    began = run.clock()

    def outcome(already: bool, tries: int, how: str) -> Outcome:
        seconds = run.clock() - began
        LOG.info('Macro: act %s: %s in %.0f ms', action.name, how, seconds * 1000)
        return Outcome(already, tries, seconds)

    if until(run, action.done, action.grace) is not None:
        return outcome(True, 0, 'already done')
    for attempt in range(action.tries):
        if attempt:
            world = run.world()
            if action.done(world):  # came after the last try's wait: no try more
                return outcome(False, attempt, f'done after {attempt} tries, late')
            if action.between is not None:
                action.between(run, world)
                if until(run, action.done, 0.0) is not None:
                    return outcome(False, attempt, f'done after {attempt} tries and the repair')
        action.act(run, attempt)
        if until(run, action.done, action.wait) is not None:
            return outcome(False, attempt + 1, f'done after {attempt + 1} tries')
    if action.late and until(run, action.done, action.late) is not None:
        return outcome(False, action.tries, f'done after {action.tries} tries, late')
    world = run.world()  # the last look: the failure names its panels (`Failed.world`)
    stop = Failed(action.name, NOT_DONE, world)
    LOG.info('Macro: act %s: failed after %d tries in %.0f ms: %s', action.name, action.tries,
             (run.clock() - began) * 1000, stop)  # fmt: skip
    raise stop
