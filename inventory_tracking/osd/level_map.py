"""Level map card: the level's rooms as iso diamonds, a player dot and POI dots.

Coordinates are Room2 tiles (map plane). The screen is isometric like the game: +x runs
down-right, +y down-left, so the dots sit where the arrow points. The card travels in the
HUD guide widget's payload and is drawn by hud/widgets.py; this module has no GTK import so
it stays unit-testable with cairo alone.
Room2 carries no walls; loaded rooms add walkable tiles from their collision grids (`walkable`),
drawn as light floor with rock left transparent, so explored parts show corridors (levels/plan.md).
Rooms never loaded are drawn slightly dimmer (`visited`, terror/tracker.py). Hostile monsters
alive are dots at their last seen position: small toned-down red for plain mobs, larger bright
magenta for a unique, champion or super unique, no rings (user, 2026-10-03: a dot per monster,
since a tinted room hid where in a big room the pack was).
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
    'herald': Tone.HERALD,  # a live Herald (terror/tracker.py)
    'mob': Tone.MOB,  # a hostile monster alive (terror/tracker.py)
    'leader': Tone.MOB_LEADER,  # a unique, champion or super unique alive
}
KIND_COLOURS = {kind: tone_rgb(tone) for kind, tone in KIND_TONES.items()}
POI_RADIUS = 5.5
KIND_RADII = {'mob': 2.0, 'leader': 3.5, 'herald': POI_RADIUS}

UNVISITED_DIM = 0.82  # rgb factor for rooms never loaded; alpha drops a little too


def room_fill(fill, visited: bool):
    """A room's fill (rgba): slightly dimmer when never loaded."""
    r, g, b, a = fill
    if not visited:
        r, g, b, a = r * UNVISITED_DIM, g * UNVISITED_DIM, b * UNVISITED_DIM, a * 0.8
    return r, g, b, a


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
    visited: tuple[int, ...] = ()  # per room: ever loaded 0/1; empty = unshaded
    live: tuple[int, int] | None = None  # (pid, player path address): the position's source (hud/live.py)

    def to_payload(self) -> dict:
        return {
            'map': {
                'rooms': [list(room) for room in self.rooms],
                'player': list(self.player),
                'pois': [[p.label, p.kind, p.x, p.y] for p in self.pois],
                'route': [list(point) for point in self.route],
                'room_kinds': list(self.room_kinds),
                'walkable': [list(grid) for grid in self.walkable],
                'visited': list(self.visited),
                'live': list(self.live) if self.live else None,
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
            visited = tuple(int(flag) for flag in data.get('visited', ()))
            live = data.get('live')
            live = (int(live[0]), int(live[1])) if live else None
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Invalid map payload') from exc
        return cls(rooms, (px, py), pois, route, kinds, walkable, visited, live)


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


def _draw_tiles(cr, transform, x, y, w, h, cells, floor=FLOOR):
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
                cr.set_source_rgba(*floor)
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
    visited = dict(zip(card.rooms, card.visited, strict=True)) if len(card.visited) == len(card.rooms) else {}
    for index, (x, y, w, h) in enumerate(card.rooms):
        if (x, y, w, h) in walled:
            continue  # its walkable tiles are drawn instead; rock stays transparent
        kind = card.room_kinds[index] if index < len(card.room_kinds) else 'room'
        fill, outline = ROOM_STYLES.get(kind, ROOM_STYLES['room'])
        fill = room_fill(fill, bool(visited.get((x, y, w, h), 1)))
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
        _draw_tiles(cr, transform, x, y, w, h, cells, room_fill(FLOOR, bool(visited.get((x, y, w, h), 1))))
    if len(card.route) >= 2:
        cr.move_to(*transform(*card.route[0]))
        for point in card.route[1:]:
            cr.line_to(*transform(*point))
        cr.set_source_rgba(0.95, 0.95, 0.95, 0.85)
        cr.set_line_width(2)
        cr.set_dash([4, 3])
        cr.stroke()
        cr.set_dash([])
    # Monsters under the level's POIs, so a pack never hides the way on.
    for poi in sorted(card.pois, key=lambda poi: poi.kind not in ('mob', 'leader')):
        colour = KIND_COLOURS.get(poi.kind, KIND_COLOURS['target'])
        radius = KIND_RADII.get(poi.kind, POI_RADIUS)
        if radius < POI_RADIUS:
            cr.arc(*transform(poi.x, poi.y), radius, 0, 2 * math.pi)
            cr.set_source_rgba(*colour, 1)
            cr.fill()
        else:
            _dot(cr, *transform(poi.x, poi.y), radius, colour, (0.1, 0.1, 0.1))
    _dot(cr, *transform(*card.player), 4.5, (1, 1, 1), (0.85, 0.2, 0.2))
