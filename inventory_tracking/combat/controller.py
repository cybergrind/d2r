"""The attack controller's decisions, apart from the game: what attack mode decides from what it sees
and from the clock, with no memory read, key or pointer in it (review.md, findings 2 and 7). The fight
in the game (macros/hunt.py) asks these and acts on the answers; the simulator asks the same ones
(sim/policy.py, the `live` candidate), so what is scored is what the game runs, as far as it goes:

- `aim_choice`: where to cast now. The policy's line, else straight at what is in reach (the elite
  first, then the nearest, AIM_BEYOND past it), and always a focal point the window lets the pointer
  reach (`Observation.aimable`): the line is scored with the focal point the cast will really have.
- `LiveAim`: `aim_choice` as a policy for the simulator, with the reach and the window of the game.
- `Aim`: whether the pointer has to be put on the line again, and whose it is meanwhile (the player's
  hand taking it somewhere is left alone until it has rested).
- `CastWatch`: the held strike input: casts seen, a press that brought no cast, a hold gone idle
  that wants a release and a new press.
- `serve`: the move the player asked for with the left button while the strikes ran: waited for,
  clicked again for them when a cast swallowed it, or given up.

Each is a small state and a step from (clock, what was seen) to what to do next, so a trace of inputs
gives a trace of actions without the game. What is still only in the fight's own loop: the order of
these steps, Death Mark and the sigil, and the weapon swap.
"""

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from inventory_tracking.combat.policy import AIM_BEYOND, REACH, Choice, Observation, Point, Policy, clear_line


RETAP_SECONDS = 0.25  # the held input idle this long between casts: released and pressed again
CAST_SECONDS = 0.8  # for the first cast animation to show after the press
REAIM_UNITS = 1.0  # the focal point this far from where the pointer was put: aimed again
STRAY_PIXELS = 25  # the pointer this far from where it was put (the player's hand): aimed again
HAND_REST = 0.2  # seconds the pointer must rest where the player's hand left it before it is aimed again
MOVE_SETTLE = 0.12  # seconds the character stands free after a move was asked for before the click is made again
MOVE_QUIET = 0.4  # seconds the strikes wait on a click the game took and that has moved nothing
MOVE_RETRY = 0.3  # seconds between two clicks made for the player
MOVE_CLICKS = 2  # clicks made for the player per move asked for
MOVE_SECONDS = 2.0  # a move asked for that has shown nothing after this long is dropped
MOVED_UNITS = 1.0  # world units the character has gone: the move is under way

Pixel = tuple[int, int]


def aim_choice(policy: Policy, seen: Observation, reachable: Iterable[int]) -> Choice | None:
    """Where to cast now: the policy's line over what is seen, else straight at one of `reachable`
    (unit ids within the blades' reach with a clear shot): the elite first, then the nearest,
    AIM_BEYOND past it, so a monster in reach is never left standing for want of a line. The focal
    point is one the pointer can be put on (`seen.aimable`); None with nothing reachable to cast at."""
    found = policy(seen)
    if found is not None:
        return found
    near = [(not seen.foes[unit].elite, math.dist(seen.origin, seen.foes[unit].at), unit) for unit in reachable]
    if not near:
        return None
    _, away, unit = min(near)
    at, away = seen.foes[unit].at, away or 1.0
    beyond = (
        at[0] + (at[0] - seen.origin[0]) / away * AIM_BEYOND,
        at[1] + (at[1] - seen.origin[1]) / away * AIM_BEYOND,
    )
    focal = seen.aimable(beyond) if seen.aimable is not None else beyond
    return Choice(focal if focal is not None else beyond, unit, 0.0)


@dataclass
class LiveAim:
    """The fight's own aim as a policy, for the simulator: `aim_choice` over the monsters within
    `reach` with a clear line (macros/sight.in_reach), through the window `aimable` (view.Viewport's
    `reachable_focal` from the character's place; None: any focal point). It yields as the policy
    does: nothing while the player is moving."""

    policy: Policy
    aimable: Callable[[Point, Point], Point | None] | None = None  # (origin, focal) -> the focal aimed at
    reach: float = REACH

    def __call__(self, seen: Observation) -> Choice | None:
        if seen.moving:
            return None
        if self.aimable is not None:
            origin, through = seen.origin, self.aimable
            seen.aimable = lambda focal: through(origin, focal)
        reachable = [
            unit
            for unit, foe in seen.foes.items()
            if math.dist(seen.origin, foe.at) <= self.reach and clear_line(seen.blocked, seen.origin, foe.at)
        ]
        return aim_choice(self.policy, seen, reachable)


@dataclass
class Aim:
    """Where the macro last put the pointer for the line, and what the player's hand has done to it."""

    hand: tuple[Pixel | None, float]  # the pointer as last seen, and since when it has been there
    aimed: tuple[Point, Point] | None = None  # (focal, the character's place) the pointer was put for

    def due(self, now: float, pointer: Pixel | None, left_at: Pixel | None, focal: Point, here: Point) -> bool:
        """Whether to put the pointer on the line now: it was never put, the focal point or the
        character has moved, or the pointer has strayed from where it was put. A pointer the player's
        hand is taking somewhere (to click a spot) is not pulled back until it has rested HAND_REST,
        or their click would land on the line."""
        strayed = pointer is None or left_at is None or math.dist(pointer, left_at) > STRAY_PIXELS
        if pointer != self.hand[0]:
            self.hand = (pointer, now)  # the pointer is somewhere new
        busy_hand = strayed and self.aimed is not None and now - self.hand[1] < HAND_REST
        stale = self.aimed is None or strayed or math.dist(self.aimed[0], focal) > REAIM_UNITS or self.aimed[1] != here
        return stale and not busy_hand

    def put(self, focal: Point, here: Point, pointer: Pixel | None) -> None:
        """The macro put the pointer at `pointer` for `focal`: that is no news of the player's hand."""
        self.aimed = (focal, here)
        self.hand = (pointer, self.hand[1])

    def forget(self) -> None:
        """Another aim of the macro's own took the pointer (a mark, a sigil): the line is aimed again."""
        self.aimed = None


RETAP, NO_CAST = 'retap', 'no cast'


@dataclass
class CastWatch:
    """The held strike input from the press on: the casts the character was seen to make."""

    began: float  # the press, or the end of a cast of the macro's own that was no strike (`excuse`)
    casts: int = 0
    acting: bool = False
    idle_since: float | None = None

    def step(self, now: float, acting: bool) -> str | None:
        """Note whether the character is casting. RETAP when the hold has been idle RETAP_SECONDS (the
        game casts once per press there: release and press again), NO_CAST when CAST_SECONDS after
        the press nothing has been cast at all (the strike is not on this input), else None."""
        if acting:
            self.casts += not self.acting
            self.acting, self.idle_since = True, None
            return None
        self.acting = False
        if not self.casts and now - self.began > CAST_SECONDS:
            return NO_CAST
        if self.idle_since is None:
            self.idle_since = now
        elif now - self.idle_since > RETAP_SECONDS:
            self.idle_since = None
            return RETAP
        return None

    def excuse(self, now: float) -> None:
        """A cast of the macro's own ran meanwhile (a mark, a sigil): it is no missing strike."""
        if not self.casts:
            self.began = now


@dataclass
class Move:
    """A move the player asked for with the left mouse button while attack mode ran."""

    at: float  # clock time of the press
    pixel: Pixel | None  # where the pointer was (root coordinates)
    origin: Point | None = None  # where the character stood, once read
    under_way: bool = False  # the character has been seen going
    free_at: float | None = None  # since when the character has stood free with the button up
    swallowed: bool = False  # pressed while a cast ran or the strike was held: the game may not have taken it
    clicks: int = 0  # clicks made for the player
    clicked_at: float = -math.inf

    def clicked(self, now: float) -> None:
        self.clicks += 1
        self.clicked_at = now


PENDING, DONE, CLICK, GAVE_UP = 'pending', 'done', 'click', 'gave up'


def serve(move: Move, now: float, here: Point, *, running: bool, acting: bool, left_down: bool) -> str:
    """What to do about the move the player asked for; it comes before any strike. The game takes no
    click while a cast runs, and a click is over before the cast is: so the strike input is let go
    at the press, nothing is cast while the move is PENDING, and when the character stands free
    with the button up and has not gone anywhere, a click the cast may have swallowed is to be made
    again for the player where they made it (CLICK; the caller makes it and calls `Move.clicked`),
    MOVE_CLICKS times at most. DONE when the character has gone and stands again, or when a click
    the game did take has had MOVE_QUIET to show a walk; GAVE_UP after MOVE_SECONDS or the clicks
    with nothing to show."""
    if move.origin is None:
        move.origin = here
    if running or math.dist(here, move.origin) > MOVED_UNITS:
        move.under_way = True
    if move.under_way:
        return DONE if not running and not left_down else PENDING  # arrived: the strikes may go on
    if left_down or acting:
        move.free_at = None  # the button still down (the game sees it), or the cast still running
        return DONE if now - move.at > MOVE_SECONDS and not left_down else PENDING
    if move.free_at is None:
        move.free_at = now
    if not move.swallowed:
        # The character was free at the press: the game took the click, and a click that moves nothing
        # (an item picked up, a chest) is not made again. The strikes wait MOVE_QUIET for a walk to show.
        return DONE if now - move.at >= MOVE_QUIET else PENDING
    if now - move.free_at < MOVE_SETTLE or now - move.clicked_at < MOVE_RETRY:
        return PENDING
    if move.clicks >= MOVE_CLICKS or now - move.at > MOVE_SECONDS or move.pixel is None:
        return GAVE_UP
    return CLICK
