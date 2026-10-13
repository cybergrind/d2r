"""Threat models a decision loop prices by: one module per kind of hostile whose harm depends on what it is doing
now and where the character will be, not only on where it stands (rca/2026-10-13/diablo.md section 5).

The decision loop (combat/harm.py, macros/safety.py) knows them only through this registry: `of(txt)` gives the
read model of a monster class or None (the loop's stand-ins then price it). A model says which missile classes it
needs read off the game (`Threat.missiles`), prices a hostile in its act against the character's way
(`Threat.exposure`: parts the loop's rollouts draw as events, raw points before the character's protection) and
offers the places its own geometry makes safer (`Threat.escapes`). No tactic is in a model: the arbiter compares
the prices of the places it is offered.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache


Point = tuple[float, float]


@dataclass(frozen=True)
class Acting:
    """A hostile as a model needs it at one look: where it stands, the client's mode (monmode.txt) and the frames
    since it was first seen in that mode, and its own missiles of the model's classes in flight (where, heading in
    radians)."""

    at: Point
    mode: int = 0
    frames: int = 0
    flying: tuple[tuple[Point, float], ...] = ()


@dataclass(frozen=True)
class Part:
    """One event of a hostile's price: `casts` (an expected count: below 1 a chance) of `points` (raw points of
    each kind a cast takes, before the character's resistances and guard), each landing with `chance`, between
    `begins` and `ends` seconds of the way."""

    casts: float
    points: tuple[tuple[str, float], ...]
    begins: float
    ends: float
    chance: float = 1.0


# (place, seconds the way is there or on its way there), the path the loop prices (combat/harm.py `harm_path`)
Legs = tuple[tuple[Point, float], ...]


@dataclass(frozen=True)
class Threat:
    missiles: frozenset[int]  # missile classes (missiles.txt) the look reads for it
    # (hostile, the character's legs, keywords seen: a clear line from it, companions: how many, resists: the
    # character's raw resistances by kind) -> its parts
    exposure: Callable[..., tuple[Part, ...]]
    # (hostile, where the character stands) -> places with a word on why each, best first
    escapes: Callable[[Acting, Point], tuple[tuple[Point, str], ...]]


@cache
def _models() -> tuple[Callable[[int], Threat | None], ...]:
    from inventory_tracking.combat.threats import diablo

    return (diablo.threat_of,)


@cache
def of(txt: int) -> Threat | None:
    """The read model of monster class `txt` (monstats *hcIdx), None when none is."""
    for model in _models():
        found = model(txt)
        if found is not None:
            return found
    return None


def missiles(txts: Mapping[int, object] | frozenset[int] | set[int]) -> frozenset[int]:
    """The missile classes the models of these monster classes read."""
    found: set[int] = set()
    for txt in txts:
        threat = of(txt)
        if threat is not None:
            found |= threat.missiles
    return frozenset(found)
