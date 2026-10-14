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
class Lying:
    """A missile that harms where it lies, as a look reads it (`Lingering`): its class, where it is, the way it goes
    (radians; None: it stands, or its way is not known) and its age in frames (as the model reckons it)."""

    missile: int
    at: Point
    heading: float | None = None
    age: int = 0


@dataclass(frozen=True)
class Lingering:
    """What a hostile's cast leaves on the ground that harms whoever stands in it after the cast, and after the
    caster's death: a threat that outlives its caster (rca/2026-10-14/run-0305-findings.md §5.6, Diablo's fire
    wall). The look reads its missiles for `lasts` seconds after a caster of the model was last seen alive."""

    missiles: frozenset[int]  # the classes read (missiles.txt)
    lasts: float  # seconds a cast's missiles can still harm after it was made
    # (missile class, where it is, where its caster stood when last seen or None, seconds it has been read) -> Lying
    read: Callable[[int, Point, Point | None, float], Lying]
    # (what lies about, the character's legs) -> parts in raw points (one correlated event each)
    exposure: Callable[[tuple[Lying, ...], Legs], tuple[Part, ...]]
    # (what lies about) -> seconds until it, and what it will still leave, is gone
    clears: Callable[[tuple[Lying, ...]], float]
    # (what lies about, where the character stands) -> places out of it with a word on why each, best first
    escapes: Callable[[tuple[Lying, ...], Point], tuple[tuple[Point, str], ...]]


@dataclass(frozen=True)
class Threat:
    missiles: frozenset[int]  # missile classes (missiles.txt) the look reads for it
    # (hostile, the character's legs, keywords seen: a clear line from it, companions: how many, resists: the
    # character's raw resistances by kind) -> its parts
    exposure: Callable[..., tuple[Part, ...]]
    # (hostile, where the character stands) -> places with a word on why each, best first
    escapes: Callable[[Acting, Point], tuple[tuple[Point, str], ...]]
    lingering: Lingering | None = None  # what its casts leave on the ground; None: nothing


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
