"""The game window's shape and the world around the character, as window fractions.

One value owns the isometric geometry: `Viewport` turns world points into window fractions (0..1 across
and down the game window) and back. Its `aspect` is width / height. This module is a leaf: it imports
nothing from the macros, so the routines, teleport and hunt modules can all use it.
"""

from dataclasses import dataclass

from inventory_tracking.native.layout import TILE_UNITS


Point = tuple[float, float]

# Where the character's feet are drawn. Host run 17:38, 2026-10-06: two summons landed 0.027 and
# 0.020 of the height above the pointer with 0.47 here, and within 0.003 across.
FEET = (0.5, 0.494)
BODY_LIFT = 0.035  # aim this much of the window height above a unit's feet
# The classic isometric view: a world unit is 16 x 8 pixels at a 600-pixel-high view.
UNIT_PIXELS = (16 / 600, 8 / 600)
AIM_LIMITS = ((0.08, 0.92), (0.08, 0.8))  # stay off the window edge and the skill bar
# Where ground may be clicked: inside the window's edges and above the skill bar.
VIEW = ((0.03, 0.97), (0.05, 0.84))
DEFAULT_ASPECT = 16 / 9  # the host's 2560 x 1418 window
# Shares of the aim's line tried in turn, the furthest first, when the focal point is off the screen.
SHARES = (1.0, 0.85, 0.7, 0.55, 0.4, 0.25)


def _inside(point: Point, limits: tuple[Point, Point]) -> bool:
    return all(low <= value <= high for value, (low, high) in zip(point, limits, strict=True))


@dataclass(frozen=True)
class Viewport:
    """The game window's shape and what it shows of the world around the character.

    Positions are world units; `origin` is the character's world (x, y). A wider window shows more
    world units across, since a unit is drawn `UNIT_PIXELS[0] / aspect` of the window wide.
    """

    aspect: float = DEFAULT_ASPECT  # width / height

    @classmethod
    def of(cls, rect: tuple[int, int, int, int]) -> Viewport:
        """The viewport of a window given as (x, y, width, height) in pixels."""
        _, _, width, height = rect
        if width <= 0 or height <= 0:
            raise ValueError(f'the window must have a positive size, not {width} x {height}')
        return cls(aspect=width / height)

    def body(self, origin: Point, x: float, y: float) -> Point:
        """Where a unit at world (x, y) is drawn: its body, `BODY_LIFT` above its feet."""
        dx, dy = x - origin[0], y - origin[1]
        return (
            FEET[0] + (dx - dy) * UNIT_PIXELS[0] / self.aspect,
            FEET[1] + (dx + dy) * UNIT_PIXELS[1] - BODY_LIFT,
        )

    def ground(self, origin: Point, x: float, y: float) -> Point:
        """Where the ground at world (x, y) is drawn: `body` without the lift onto a body."""
        across, down = self.body(origin, x, y)
        return across, down + BODY_LIFT

    def world(self, origin: Point, across: float, down: float) -> Point:
        """The ground point drawn at window fraction (across, down): the inverse of `ground`."""
        units_across = (across - FEET[0]) * self.aspect / UNIT_PIXELS[0]
        units_down = (down - FEET[1]) / UNIT_PIXELS[1]
        return origin[0] + (units_across + units_down) / 2, origin[1] + (units_down - units_across) / 2

    def on_screen(self, point: Point) -> bool:
        """Whether a window fraction is inside `AIM_LIMITS`: where a cast may be aimed."""
        return _inside(point, AIM_LIMITS)

    def in_view(self, point: Point) -> bool:
        """Whether a window fraction is inside `VIEW`: where ground may be clicked."""
        return _inside(point, VIEW)

    def hop_in_view(self, dx: int, dy: int) -> bool:
        """Whether a hop of (dx, dy) tiles lands in view from anywhere on the tile it starts from.

        The view is not round: it shows 23 world units up the screen and 18 down to the skill bar, so a
        gap that is crossed going up may not be crossed coming down.
        """
        across, down = (dx - dy) * TILE_UNITS, (dx + dy) * TILE_UNITS  # as routines.screen_fraction
        (left, right), (top, bottom) = VIEW
        slack = TILE_UNITS / 2  # the character stands anywhere on its tile, the spot anywhere on the other
        wide, high = UNIT_PIXELS[0] / self.aspect, UNIT_PIXELS[1]
        return (
            left <= FEET[0] + (across - slack) * wide
            and FEET[0] + (across + slack) * wide <= right
            and top <= FEET[1] + (down - slack) * high
            and FEET[1] + (down + slack) * high <= bottom
        )

    def aim(self, origin: Point, focal: Point) -> Point | None:
        """The window fraction to put the pointer on for a cast at world `focal`, or None.

        That is the ground of `reachable_focal`: the focal point itself, or the furthest point of its
        line that is on the screen.
        """
        reachable = self.reachable_focal(origin, focal)
        return None if reachable is None else self.ground(origin, *reachable)

    def reachable_focal(self, origin: Point, focal: Point) -> Point | None:
        """The world point a cast at `focal` really lands on, or None when no point of its line is on screen.

        `focal` itself when its ground is on screen; else the first point of `SHARES` along the line from
        `origin` to `focal` whose ground is on screen. The blades fly their length along the line whatever
        the focal distance, so only where they meet moves.
        """
        if self.on_screen(self.ground(origin, *focal)):
            return focal
        for share in SHARES:
            point = (origin[0] + (focal[0] - origin[0]) * share, origin[1] + (focal[1] - origin[1]) * share)
            if self.on_screen(self.ground(origin, *point)):
                return point
        return None
