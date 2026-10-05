"""Ground marks: the level map's dots drawn on the game view itself (user, 2026-10-05).

A mark is a map-plane point in Room2 tiles, like the map card's dots. The game view is isometric
with the player at a fixed point of the window: +x runs down-right, +y down-left, and one tile's
floor diamond is twice as wide as it is tall. `project` turns a tile offset from the player into
window pixels; a mark outside the window is pulled back along the line from the player to the
window's edge, so it still says which way to go. The constants (HUD.ground) are the classic
800x600 view scaled to the window height and are not calibrated in-game yet; D2R's camera also
has a slight perspective this ignores. Pure data and arithmetic: no GTK/Pango.
"""

from inventory_tracking.config import HUD, HudGroundConfig
from inventory_tracking.osd.level_map import MapCard


def ground_payload(card: MapCard, config: HudGroundConfig = HUD.ground) -> dict | None:
    """The card's dots of the configured kinds, with the player they are relative to; None = nothing to mark."""
    marks = [[poi.kind, poi.x, poi.y] for poi in card.pois if poi.kind in config.kinds]
    if not (config.enabled and marks):
        return None
    return {'player': list(card.player), 'marks': marks, 'live': list(card.live) if card.live else None}


def ground_marks(payload) -> tuple[tuple[float, float], list[tuple[str, float, float]]]:
    try:
        px, py = (float(v) for v in payload['player'])
        return (px, py), [(str(kind), float(x), float(y)) for kind, x, y in payload['marks']]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid ground payload') from exc


def project(dx: float, dy: float, width: float, height: float, config: HudGroundConfig = HUD.ground):
    """Window pixel of the point (dx, dy) tiles from the player."""
    half_width = config.tile_height * height  # a tile's diamond is 2:1, so its half-width is its height
    return (
        config.player_x * width + (dx - dy) * half_width,
        config.player_y * height + (dx + dy) * half_width / 2,
    )


def place_mark(dx: float, dy: float, width: float, height: float, config: HudGroundConfig = HUD.ground):
    """(x, y, on_screen): the projected point, or where the line to it leaves the window's inset frame."""
    x, y = project(dx, dy, width, height, config)
    inset = config.edge_inset * height
    if inset <= x <= width - inset and inset <= y <= height - inset:
        return x, y, True
    origin_x, origin_y = project(0, 0, width, height, config)
    reach = 1.0
    for value, origin, low, high in ((x, origin_x, inset, width - inset), (y, origin_y, inset, height - inset)):
        if value > high:
            reach = min(reach, (high - origin) / (value - origin))
        elif value < low:
            reach = min(reach, (low - origin) / (value - origin))
    return origin_x + (x - origin_x) * reach, origin_y + (y - origin_y) * reach, False
