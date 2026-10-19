"""The pickup key's run mode: how much of a level one press runs (the player, 2026-10-14; rca/2026-10-14/kp1-mode.md).

- **goal** (default): go to the route's goal, fighting what is on the way (macros/goals.py `clear_way`).
- **full clear**: the whole level first, then the route's stages. Default on a terror zone (terror/tracker.py).

A double press (exactly two, within DOUBLE) switches the mode once the window after the second closes, so a mashed
key switches nothing; the switch lapses on leaving the level. Pairs are judged by the clock, not the hunt's looks:
a pair whose window closed unseen is `owed` (rca/2026-10-14/run-1904-findings.md §3.3). Pure: the hunt records
`Taps` under its mailbox lock and judges them at a look (`doubles`).
"""

import math
from dataclasses import dataclass, replace

from inventory_tracking.routes.model import ENTER, FIGHT, STAND, USE, Script


# Seconds between a double press's two presses; the player's pairs came 0.20-0.29 s apart (kp1-mode.md §2).
DOUBLE = 0.35
TERROR = 'terror zone'
AGENDA = 'the terror zone loop'  # macros/tzloop.py: the agenda's targets, then the route's stages
SWITCHED = 'switched by the player'


@dataclass(frozen=True)
class Taps:
    """The last group of presses, each within DOUBLE of the one before. `judged`: acted on as a double press.
    `owed`: earlier groups' double presses no look acted on, as (first, last)."""

    first: float = -math.inf
    last: float = -math.inf
    count: int = 0
    judged: bool = False
    owed: tuple[tuple[float, float], ...] = ()


def tapped(taps: Taps, at: float) -> Taps:
    """`taps` with a press at `at`: joins the group within DOUBLE, else starts one (an unjudged pair ended is owed)."""
    if 0.0 <= at - taps.last <= DOUBLE:
        return replace(taps, last=at, count=taps.count + 1)
    owed = (*taps.owed, (taps.first, taps.last)) if taps.count == 2 and not taps.judged else taps.owed
    return Taps(at, at, 1, owed=owed)


def doubled(taps: Taps, now: float) -> bool:
    """Whether the group is an unjudged pair whose window has closed."""
    return taps.count == 2 and not taps.judged and now - taps.last > DOUBLE


def doubles(taps: Taps, now: float) -> tuple[tuple[tuple[float, float], ...], Taps]:
    """The double presses to act on at `now` (owed, then the group's own), and the taps with them acted on."""
    found = taps.owed
    if doubled(taps, now):
        found = (*found, (taps.first, taps.last))
        taps = replace(taps, judged=True)
    return found, replace(taps, owed=())


@dataclass(frozen=True)
class Mode:
    """`clear` the whole level, else its goal; `why` it is not the default ('' when it is)."""

    clear: bool
    why: str = ''
    agenda: bool = False  # the terror zone loop (macros/tzloop.py): the agenda's targets, then the route's stages


def mode_of(area: int | None, terror: bool | None, switched: tuple[int, bool] | None) -> Mode:
    """The mode on `area`: the player's switch made on it, else full clear on a terror zone, else the goal."""
    if switched is not None and area is not None and switched[0] == area:
        return Mode(switched[1], SWITCHED)
    if terror:
        return Mode(True, TERROR)
    return Mode(False)


def aim_of(script: Script | None) -> str | None:
    """The name of the route's last boss or mark, for the log; None without a route."""
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
    if mode.agenda:
        return f'the agenda, then {aim}' if aim else 'the agenda'
    if mode.clear:
        return f'full clear ({mode.why or SWITCHED})'
    head = f'to {aim}, clearing the way' if aim else 'no route on this level: the key works around the character'
    return f'{head} ({mode.why})' if mode.why else head


def badge(mode: Mode | None) -> str | None:
    """The HUD's word for the mode (hud/process.py `ModeBeacon`): shown only for a full clear."""
    if mode is None or not mode.clear:
        return None
    if mode.agenda:
        return 'TZ LOOP'
    return 'CLEAR TZ' if mode.why == TERROR else 'CLEAR'
