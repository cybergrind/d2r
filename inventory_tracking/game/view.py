"""The game window's shape and the world around the character, as window fractions.

One value owns the isometric geometry: `Viewport` turns world points into window fractions (0..1 across
and down the game window) and back. Its `aspect` is width / height. This module is a leaf: it imports
nothing from the macros, so the routines, teleport and hunt modules can all use it.
"""

from dataclasses import dataclass

from inventory_tracking.levels.geometry import Point
from inventory_tracking.native.layout import TILE_UNITS


# Where the character's feet are drawn. Host run 17:38, 2026-10-06: two summons landed 0.027 and
# 0.020 of the height above the pointer with 0.47 here, and within 0.003 across.
FEET = (0.5, 0.494)
BODY_LIFT = 0.035  # aim this much of the window height above a unit's feet
# The classic isometric view: a world unit is 16 x 8 pixels at a 600-pixel-high view.
UNIT_PIXELS = (16 / 600, 8 / 600)
AIM_LIMITS = ((0.08, 0.92), (0.08, 0.8))  # stay off the window edge and the skill bar
# Where ground may be clicked: inside the window's edges and above the skill bar.
VIEW = ((0.03, 0.97), (0.05, 0.84))
# A teleport may also be aimed beside the skill bar, down to CORNER_BOTTOM, where the window shows
# ground left and right of it (user, 2026-10-11: let the macro try the corners; with them the window
# shows 34 units down the screen where it showed 26, and a cliff 25 units wide is hopped going down as
# it is going up). The bar is taken as HUD_HALF window heights to each side of the middle, by what the
# game took (Far Oasis, 02:16 on 2026-10-11, the host's 2560 x 1418): casts aimed 0.67, 0.69, 0.72 and
# 0.85 heights from the middle, 0.89 to 0.92 down, landed on the spot; one 0.63 from the middle did
# nothing. Confirmed in the game: 11 of 11 hops aimed there landed (03:11 to 03:21 on 2026-10-11).
# `CORNERS` is the switch (tests turn it off for the plain view).
CORNER_BOTTOM = 0.95
HUD_HALF = 0.70
CORNERS = [True]  # one switch for every Viewport; a list so it is changed in place
DEFAULT_ASPECT = 16 / 9  # the host's 2560 x 1418 window
# Shares of the aim's line tried in turn, the furthest first, when the focal point is off the screen.
SHARES = (1.0, 0.85, 0.7, 0.55, 0.4, 0.25)
# The mark's aim shape (2026-10-25, rca/2026-10-25/mark-at-spawn-findings.md §3; the coordinator after the 11:37:30
# spawn: 113 Death Marks of the session refused as "off the screen" by AIM_LIMITS, 53 of them below 0.80 where the
# ground shows). Measured on 198 shots of the host's 2560 x 1418 window (11:37:25-34, Palace Cellar 3) by the pixels
# that stay the same under the moving world, and on grid crops of one shot: the skill bar's top is at 0.920 from 0.29
# to 0.71 across; the life orb and its angel rise to 0.845 from 0.155 to 0.29; the mana orb's demon's horns to 0.815
# from 0.705 to 0.86; outside them (x < 0.15, x > 0.865) the ground shows down to the window's bottom. At the top the
# desktop's bar covers the window's first 0.015, and the companions' portraits (with their names) the corner left of
# 0.135 down to 0.075. Each limit keeps MARK_EDGE off the outline. `markable` is the mark's (macros/buffs.py
# MARK_SHAPE); the other casts keep AIM_LIMITS, not measured for them.
MARK_EDGE = 0.01
MARK_TOP = 0.015 + MARK_EDGE
MARK_PORTRAITS = (0.135 + MARK_EDGE, 0.075 + MARK_EDGE)  # left of across, above down: the portraits
# (from this across on, the lowest down the mark may be aimed): the bottom corner, the angel and life orb, the bar,
# the mana orb and its demon, the bottom corner
MARK_FLOOR = (
    (0.0, 1.0 - MARK_EDGE),
    (0.155 - MARK_EDGE, 0.845 - MARK_EDGE),
    (0.29, 0.920 - MARK_EDGE),
    (0.705 - MARK_EDGE, 0.815 - MARK_EDGE),
    (0.865 + MARK_EDGE, 1.0 - MARK_EDGE),
)


# HOP_SHAPE (2026-10-25, game 173 at 17:16:56-17:17:13): a Teleport toward a Small Charm 22.6 away was aimed at
# (0.797, 0.826) of the window, inside VIEW (down to 0.84) but on the mana orb's demon (its horns rise to 0.815 from
# 0.705 to 0.86 across, MARK_FLOOR): four presses cast nothing and the run stood 17 s. True: `hop_view` also keeps under
# the HUD's measured outline (`hud_floor`). False: VIEW and the corners alone, as before.
HOP_SHAPE = True


def hud_floor(across: float) -> float:
    """The lowest window fraction down at `across` above the HUD's measured outline (MARK_FLOOR)."""
    return next((low for start, low in reversed(MARK_FLOOR) if across >= start), MARK_FLOOR[0][1])


def markable(point: Point) -> bool:
    """Whether a window fraction is inside the mark's aim shape (MARK_FLOOR's text): off the window's edges, the
    desktop's bar, the portraits and the HUD's outline."""
    across, down = point
    if not (MARK_EDGE <= across <= 1.0 - MARK_EDGE and down >= MARK_TOP):
        return False
    if across < MARK_PORTRAITS[0] and down < MARK_PORTRAITS[1]:
        return False
    return down <= hud_floor(across)


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

    def hop_view(self, point: Point) -> bool:
        """Whether a teleport may be aimed at a window fraction: inside `VIEW`, or beside the skill bar
        down to CORNER_BOTTOM while the corners are on."""
        across, down = point
        if HOP_SHAPE and down > hud_floor(across):
            return False
        if _inside(point, VIEW):
            return True
        (left, right), (_, bottom) = VIEW
        beside = abs(across - 0.5) >= HUD_HALF / self.aspect
        return CORNERS[0] and beside and left <= across <= right and bottom < down <= CORNER_BOTTOM

    def hop_between(self, dx: int, dy: int) -> bool:
        """Whether a hop of (dx, dy) tiles from a tile's centre to another's lands where a teleport may
        be aimed (`hop_view`): `hop_in_view` without its slack for where on the two tiles the hop begins
        and ends."""
        across, down = (dx - dy) * TILE_UNITS, (dx + dy) * TILE_UNITS
        return self.hop_view((FEET[0] + across * UNIT_PIXELS[0] / self.aspect, FEET[1] + down * UNIT_PIXELS[1]))

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
