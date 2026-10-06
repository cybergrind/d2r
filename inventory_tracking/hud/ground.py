"""Ground marks: the level map's dots drawn on the game view itself (user, 2026-10-05).

A mark is a map-plane point in Room2 tiles, like the map card's dots. The game view is isometric
with the player at a fixed point of the window: +x runs down-right, +y down-left, and one tile's
floor diamond is twice as wide as it is tall. `project` turns a tile offset from the player into
window pixels; a mark outside the window becomes an arrow towards it on a ring around the player
(close to the player on entering a level, then further out), so it still says which way to go.
The constants (HUD.ground) are the classic
800x600 view scaled to the window height and are not calibrated in-game yet; D2R's camera also
has a slight perspective this ignores. Pure data and arithmetic: no GTK/Pango.
"""

import math
import zlib

from inventory_tracking.config import HUD, HudGroundConfig
from inventory_tracking.osd.level_map import MapCard


def ground_payload(card: MapCard, config: HudGroundConfig = HUD.ground) -> dict | None:
    """The card's dots of the configured kinds, with the player they are relative to; None = nothing
    to mark. `level` tells one level's marks from the next. A mark is [kind, x, y], plus its path
    address when the canvas can read where it is now (hud/live.py)."""
    marks = [[p.kind, p.x, p.y, *([p.path] if p.path else [])] for p in card.pois if p.kind in config.kinds]
    if not (config.enabled and marks):
        return None
    level = zlib.crc32(repr(card.rooms).encode())  # the same rooms = the same level (hud/live.py Entrance)
    return {'player': list(card.player), 'marks': marks, 'live': list(card.live) if card.live else None, 'level': level}


def ground_marks(payload) -> tuple[tuple[float, float], list[tuple[str, float, float]]]:
    try:
        px, py = (float(v) for v in payload['player'])
        return (px, py), [(str(kind), float(x), float(y)) for kind, x, y, *_ in payload['marks']]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid ground payload') from exc


def project(dx: float, dy: float, width: float, height: float, config: HudGroundConfig = HUD.ground):
    """Window pixel of the point (dx, dy) tiles from the player."""
    half_width = config.tile_height * height  # a tile's diamond is 2:1, so its half-width is its height
    return (
        config.player_x * width + (dx - dy) * half_width,
        config.player_y * height + (dx + dy) * half_width / 2,
    )


def arrow_reach(age: float | None, config: HudGroundConfig = HUD.ground) -> float:
    """The arrow ring's radius (fraction of the window height) `age` seconds after entering the level."""
    if age is None or age >= config.arrow_seconds:
        return config.arrow_rest
    if age <= config.arrow_hold:
        return config.arrow_near
    t = (age - config.arrow_hold) / (config.arrow_seconds - config.arrow_hold)
    return config.arrow_near + (config.arrow_rest - config.arrow_near) * t * t * (3 - 2 * t)  # ease in and out


def arrow_shown(kind: str, dx: float, dy: float, config: HudGroundConfig = HUD.ground) -> bool:
    """Whether a mark of `kind` out of view, (dx, dy) tiles from the player, gets its arrow."""
    limit = config.arrow_range.get(kind)
    return limit is None or math.hypot(dx, dy) <= limit


def place_mark(
    dx: float, dy: float, width: float, height: float, config: HudGroundConfig = HUD.ground, reach: float | None = None
):
    """(x, y, on_screen): the projected point, or where an arrow towards it stands: `reach` (default
    the resting ring, a fraction of the window height) from the player along the line to the point."""
    x, y = project(dx, dy, width, height, config)
    inset = config.edge_inset * height
    if inset <= x <= width - inset and inset <= y <= height - inset:
        return x, y, True
    origin_x, origin_y = project(0, 0, width, height, config)
    radius = (config.arrow_rest if reach is None else reach) * height
    distance = math.hypot(x - origin_x, y - origin_y)
    return origin_x + (x - origin_x) / distance * radius, origin_y + (y - origin_y) / distance * radius, False
