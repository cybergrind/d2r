"""The pickup key's run mode: how much of a level one press runs (the player's ruling of 2026-10-14,
rca/2026-10-14/kp1-mode.md).

- **goal** (the default): the level run goes to the level's goal (the route's stages of the level: the
  River of Flame to the door of the Chaos Sanctum, the Chaos Sanctuary to Diablo) and fights what it meets
  on the way (macros/goals.py `clear_way`). Entered from the waypoint the River is cleared about half way;
  from the City of the Damned all the way. The rest of the level is left.
- **full clear**: the whole level first (what is in sight, what the tracker remembers alive, the rooms not
  explored yet), then the route's stages. The default on a level that is a terror zone now (terror/tracker.py
  `terrorized`), or when the player switches to it.

The switch is a double press of the pickup key: exactly two presses, the second within DOUBLE seconds of the
first. Both presses are level-run presses as any other (the run starts or goes on); the mode turns over once
the window after the second has passed with no third press, so a mashed key (three presses and more, each
0.19 to 0.4 s apart: 109 KP_1 presses since the level run, rca/2026-10-14/kp1-mode.md §2) switches nothing.
The switch holds for the level it was made on and lapses on any other (a town visit included).

A double press is judged by the clock, not by when the hunt looks: its window closes DOUBLE after its second press
whether or not a look comes then, and a pair whose window closed before the next look still switches (`owed`). The
game of 22:04 on 2026-10-14 (rca/2026-10-14/run-1904-findings.md §3.3) lost two of the player's pairs: a Blade Warp
in flight and then the paused run made no look in their windows, and the next press 1.2 s and 2.3 s later began a new
group over them. Every pair is honoured, the one that starts a run included (the player's ruling of 2026-10-14).

Pure: the presses (`Taps`) are recorded by the hunt under its mailbox lock as they are posted, and judged at a
look (`doubles`); nothing here reads the game.
"""

import math
from dataclasses import dataclass, replace

from inventory_tracking.routes.model import ENTER, FIGHT, STAND, USE, Script


# Seconds: the second press of a double press comes within this of the first. The player's own pairs since the
# level run came 0.20 to 0.29 s apart (session logs 2026-10-13 23:56 to 2026-10-14 15:16, kp1-mode.md §2).
DOUBLE = 0.35
TERROR = 'terror zone'
SWITCHED = 'switched by the player'


@dataclass(frozen=True)
class Taps:
    """The pickup key's last presses, one group: each came within DOUBLE of the one before. `judged`: the group
    has been looked at as a double press (it turns the mode over once). `owed`: the double presses of the groups
    before it that no look acted on, as (first, last) in the order they were made: each turns the mode over at the
    next look (`doubles`)."""

    first: float = -math.inf
    last: float = -math.inf
    count: int = 0
    judged: bool = False
    owed: tuple[tuple[float, float], ...] = ()


def tapped(taps: Taps, at: float) -> Taps:
    """`taps` with a press made at `at`: one more of the group when within DOUBLE of its last, else a new group. A
    group it ends that was a double press no look acted on is owed (its window closed by the clock)."""
    if 0.0 <= at - taps.last <= DOUBLE:
        return replace(taps, last=at, count=taps.count + 1)
    owed = (*taps.owed, (taps.first, taps.last)) if taps.count == 2 and not taps.judged else taps.owed
    return Taps(at, at, 1, owed=owed)


def doubled(taps: Taps, now: float) -> bool:
    """Whether the group is a double press to act on now: exactly two presses, the window after the second over
    (a third would make it a mashed key), not acted on yet."""
    return taps.count == 2 and not taps.judged and now - taps.last > DOUBLE


def doubles(taps: Taps, now: float) -> tuple[tuple[tuple[float, float], ...], Taps]:
    """The double presses to act on at a look at `now`, in the order made, as (first, last): those owed, then the
    group's own once its window is over; and the presses with them acted on."""
    found = taps.owed
    if doubled(taps, now):
        found = (*found, (taps.first, taps.last))
        taps = replace(taps, judged=True)
    return found, replace(taps, owed=())


@dataclass(frozen=True)
class Mode:
    """How much of the level a run works: `clear` the whole of it, else its goal; `why` the mode is not the
    default (`TERROR`, `SWITCHED`), '' when it is."""

    clear: bool
    why: str = ''


def mode_of(area: int | None, terror: bool | None, switched: tuple[int, bool] | None) -> Mode:
    """The mode on level `area`: the player's switch where it was made on this level ((level, full clear)),
    else full clear on a terror zone, else the goal."""
    if switched is not None and area is not None and switched[0] == area:
        return Mode(switched[1], SWITCHED)
    if terror:
        return Mode(True, TERROR)
    return Mode(False)


def aim_of(script: Script | None) -> str | None:
    """What a level's route goes to in the end, for the log: its last stage that is gone to (a boss fought, a door
    entered, an object used, a mark stood at), by name. None: the level has no route."""
    if script is None:
        return None
    for stage in reversed(script.stages):
        if stage.kind == FIGHT:
            return stage.boss
        if stage.kind in (ENTER, USE, STAND) and stage.mark:
            return stage.mark
    return None


def said(mode: Mode, aim: str | None) -> str:
    """The mode as the log says it (`Macro: run: ...`)."""
    if mode.clear:
        return f'full clear ({mode.why or SWITCHED})'
    head = f'to {aim}, clearing the way' if aim else 'no route on this level: the key works around the character'
    return f'{head} ({mode.why})' if mode.why else head


def badge(mode: Mode | None) -> str | None:
    """The HUD's word for the mode (hud/process.py `ModeBeacon`): shown only for a full clear."""
    if mode is None or not mode.clear:
        return None
    return 'CLEAR TZ' if mode.why == TERROR else 'CLEAR'
