"""Level map card: the level's rooms as iso diamonds, a player dot and POI dots.

Coordinates are Room2 tiles (map plane). The screen is isometric like the game: +x runs
down-right, +y down-left, so the dots sit where the arrow points. The card travels in the
HUD guide widget's payload and is drawn by hud/widgets.py; this module has no GTK import so
it stays unit-testable with cairo alone.
Room2 carries no walls; loaded rooms add walkable tiles from their collision grids (`walkable`),
drawn as light floor with rock left transparent, so explored parts show corridors (levels/plan.md).
"""

import math
from dataclasses import dataclass

from inventory_tracking.presentation import Tone, tone_rgb


# Room fill/outline by kind. Edges (outdoor level borders: fences, cliffs) are darker and dimmer,
# so the walkable area stands out; Room2 has no finer wall data (levels/plan.md).
ROOM_STYLES = {
    'room': ((0.62, 0.56, 0.42, 0.35), (0.70, 0.61, 0.38, 0.55)),
    'edge': ((0.20, 0.17, 0.14, 0.85), (0.35, 0.30, 0.22, 0.60)),
}

# One colour per POI kind for rows, arrows and dots (user, 2026-09-30): next level green,
# previous level purple, waypoint blue, POI (boss, chest, rune, shrine) bright yellow.
# Unknown kinds use the POI colour.
KIND_TONES = {
    'stairs': Tone.LEVEL_NEXT,
    'previous': Tone.LEVEL_PREVIOUS,
    'waypoint': Tone.WAYPOINT,
    'target': Tone.POI,
    'exit': Tone.EXIT,  # an exit whose destination is not known yet
}
KIND_COLOURS = {kind: tone_rgb(tone) for kind, tone in KIND_TONES.items()}


@dataclass(frozen=True)
class MapPoi:
    label: str
    kind: str
    x: float
    y: float


@dataclass(frozen=True)
class MapCard:
    rooms: tuple[tuple[int, int, int, int], ...]  # x, y, width, height in tiles
    player: tuple[float, float]
    pois: tuple[MapPoi, ...] = ()
    route: tuple[tuple[float, float], ...] = ()  # player → room centres → POI, in tiles (mazes only)
    room_kinds: tuple[str, ...] = ()  # per room: 'room' or 'edge' (outdoor level border); empty = all 'room'
    walkable: tuple[tuple[int, int, int, int, str], ...] = ()  # x, y, w, h tiles, '1'/'0' per tile

    def to_payload(self) -> dict:
        return {
            'map': {
                'rooms': [list(room) for room in self.rooms],
                'player': list(self.player),
                'pois': [[p.label, p.kind, p.x, p.y] for p in self.pois],
                'route': [list(point) for point in self.route],
                'room_kinds': list(self.room_kinds),
                'walkable': [list(grid) for grid in self.walkable],
            }
        }

    @classmethod
    def from_payload(cls, value) -> MapCard:
        try:
            data = value['map']
            rooms = tuple((int(x), int(y), int(w), int(h)) for x, y, w, h in data['rooms'])
            px, py = (float(v) for v in data['player'])
            pois = tuple(MapPoi(str(label), str(kind), float(x), float(y)) for label, kind, x, y in data['pois'])
            route = tuple((float(x), float(y)) for x, y in data.get('route', ()))
            kinds = tuple(str(kind) for kind in data.get('room_kinds', ()))
            walkable = tuple((int(x), int(y), int(w), int(h), str(c)) for x, y, w, h, c in data.get('walkable', ()))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Invalid map payload') from exc
        return cls(rooms, (px, py), pois, route, kinds, walkable)


def project(x: float, y: float) -> tuple[float, float]:
    return x - y, (x + y) / 2


def fit(card: MapCard, width: float, height: float, *, margin: float = 10):
    """Map-plane (x, y) → pixel transform that fits every room corner and dot in the box."""
    points = [(x + dx, y + dy) for x, y, w, h in card.rooms for dx in (0, w) for dy in (0, h)]
    points += [card.player, *((p.x, p.y) for p in card.pois)]
    projected = [project(x, y) for x, y in points]
    min_x, max_x = min(p[0] for p in projected), max(p[0] for p in projected)
    min_y, max_y = min(p[1] for p in projected), max(p[1] for p in projected)
    scale = min((width - 2 * margin) / max(max_x - min_x, 1e-9), (height - 2 * margin) / max(max_y - min_y, 1e-9))
    offset_x = (width - (max_x - min_x) * scale) / 2
    offset_y = (height - (max_y - min_y) * scale) / 2

    def transform(x: float, y: float) -> tuple[float, float]:
        sx, sy = project(x, y)
        return offset_x + (sx - min_x) * scale, offset_y + (sy - min_y) * scale

    return transform


def _dot(cr, x, y, radius, fill, ring):
    cr.arc(x, y, radius, 0, 2 * math.pi)
    cr.set_source_rgba(*fill, 1)
    cr.fill_preserve()
    cr.set_source_rgba(*ring, 1)
    cr.set_line_width(1.5)
    cr.stroke()


FLOOR = (0.80, 0.72, 0.52, 0.80)


def _draw_tiles(cr, transform, x, y, w, h, cells):
    """One iso parallelogram per run of walkable tiles in a row; rock is left transparent."""
    if len(cells) != w * h:
        return
    for row in range(h):
        line = cells[row * w : (row + 1) * w]
        start = 0
        while start < w:
            end = start
            while end < w and line[end] == line[start]:
                end += 1
            corners = [
                transform(x + start, y + row),
                transform(x + end, y + row),
                transform(x + end, y + row + 1),
                transform(x + start, y + row + 1),
            ]
            cr.move_to(*corners[0])
            for corner in corners[1:]:
                cr.line_to(*corner)
            cr.close_path()
            if line[start] == '1':
                cr.set_source_rgba(*FLOOR)
                cr.fill()
            else:
                cr.new_path()
            start = end


def draw_map(cr, width: float, height: float, card: MapCard):
    """No background (user, 2026-09-30): the game shows around the level and through rock."""
    if not card.rooms:
        return
    transform = fit(card, width, height)
    cr.set_line_width(1)
    walled = {(x, y, w, h) for x, y, w, h, _ in card.walkable}
    for index, (x, y, w, h) in enumerate(card.rooms):
        if (x, y, w, h) in walled:
            continue  # its walkable tiles are drawn instead; rock stays transparent
        kind = card.room_kinds[index] if index < len(card.room_kinds) else 'room'
        fill, outline = ROOM_STYLES.get(kind, ROOM_STYLES['room'])
        corners = [transform(x, y), transform(x + w, y), transform(x + w, y + h), transform(x, y + h)]
        cr.move_to(*corners[0])
        for corner in corners[1:]:
            cr.line_to(*corner)
        cr.close_path()
        cr.set_source_rgba(*fill)
        cr.fill_preserve()
        cr.set_source_rgba(*outline)
        cr.stroke()
    for x, y, w, h, cells in card.walkable:
        _draw_tiles(cr, transform, x, y, w, h, cells)
    if len(card.route) >= 2:
        cr.move_to(*transform(*card.route[0]))
        for point in card.route[1:]:
            cr.line_to(*transform(*point))
        cr.set_source_rgba(0.95, 0.95, 0.95, 0.85)
        cr.set_line_width(2)
        cr.set_dash([4, 3])
        cr.stroke()
        cr.set_dash([])
    for poi in card.pois:
        _dot(cr, *transform(poi.x, poi.y), 5.5, KIND_COLOURS.get(poi.kind, KIND_COLOURS['target']), (0.1, 0.1, 0.1))
    _dot(cr, *transform(*card.player), 4.5, (1, 1, 1), (0.85, 0.2, 0.2))
