"""Level map card: the level's rooms as iso diamonds, a player dot and POI dots.

Coordinates are Room2 tiles (map plane). The screen is isometric like the game: +x runs
down-right, +y down-left, so the dots sit where the arrow points. The card travels in the
HUD guide widget's payload and is drawn by hud/widgets.py; this module has no GTK import so
it stays unit-testable with cairo alone.
Room2 carries no walls; loaded rooms add walkable sub-tiles from their collision grids (`walkable`),
drawn as light floor with rock left transparent, so explored parts show corridors (levels/plan.md).
Rooms never loaded are drawn slightly dimmer (`visited`, terror/tracker.py). Hostile monsters
alive are dots at their last seen position: small toned-down red for plain mobs, larger bright
magenta for a unique, champion or super unique, no rings (user, 2026-10-03: a dot per monster,
since a tinted room hid where in a big room the pack was).
A level too big for the card at a readable size is not shrunk to fit (user, 2026-10-06: Great
Marsh was a speck): one that would fall below `WHOLE_SCALE` shows the part around the player at
`LOCAL_SCALE` instead, and each of the level's own dots outside it is an arrowhead on the card's edge, towards it.
That view is much more floor per pixel, so its rooms are fainter (`LOCAL_ALPHA`; user, 2026-10-06:
too much colour over the game). `MapCard.whole` asks for the whole level anyway (Win+C, levels/guide.py).
"""

import math
import re
from dataclasses import dataclass

from inventory_tracking.levels.model import unpack_cells
from inventory_tracking.native.layout import TILE_UNITS
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
    'danger': Tone.MOB_DANGER,  # a monster of a deadly pack (terror/danger.py)
    'caution': Tone.MOB_CAUTION,  # a monster of a pack to be careful with
    'pack': Tone.MOB_DANGER,  # a deadly pack's centre: the ground arrow towards it, no dot of its own
    'elite': Tone.MOB_LEADER,  # a deadly pack's leader: a leader's dot ringed in the pack's colour
}
KIND_COLOURS = {kind: tone_rgb(tone) for kind, tone in KIND_TONES.items()}
POI_RADIUS = 5.5
MONSTER_KINDS = frozenset(('mob', 'leader', 'herald', 'danger', 'caution', 'pack', 'elite'))  # from terror/tracker.py
KIND_RADII = {'mob': 2.0, 'caution': 3.0, 'leader': 3.5, 'danger': 3.0, 'elite': 4.5, 'herald': POI_RADIUS}
ELITE_RING = 2.5  # the elite dot's ring, in its pack's colour
MONSTER_ORDER = ('mob', 'caution', 'leader', 'danger', 'elite')  # drawn in this order, under everything else

# Card pixels per projected tile unit, at HUD scale 1 (the game view is about 190). A level is
# drawn whole down to WHOLE_SCALE; a bigger one is drawn around the player at LOCAL_SCALE, where
# the card spans a bit over two screens each way: enough to tell monsters apart.
WHOLE_SCALE = 7.0
LOCAL_SCALE = 12.0
LOCAL_ALPHA = 0.55  # alpha factor for rooms and floor in the local view
PIN_INSET = 9.0  # an edge arrowhead's tip stands this far inside the card

UNVISITED_DIM = 0.82  # rgb factor for rooms never loaded; alpha drops a little too


def room_fill(fill, visited: bool, alpha: float = 1.0):
    """A room's fill (rgba): slightly dimmer when never loaded; `alpha` scales its opacity."""
    r, g, b, a = fill
    if not visited:
        r, g, b, a = r * UNVISITED_DIM, g * UNVISITED_DIM, b * UNVISITED_DIM, a * 0.8
    return r, g, b, a * alpha


@dataclass(frozen=True)
class MapPoi:
    label: str
    kind: str
    x: float
    y: float
    path: int = 0  # address of a monster's dynamic path, when the HUD can follow it (hud/live.py)


@dataclass(frozen=True)
class MapCard:
    rooms: tuple[tuple[int, int, int, int], ...]  # x, y, width, height in tiles
    player: tuple[float, float]
    pois: tuple[MapPoi, ...] = ()
    route: tuple[tuple[float, float], ...] = ()  # player → room centres → POI, in tiles (mazes only)
    room_kinds: tuple[str, ...] = ()  # per room: 'room' or 'edge' (outdoor level border); empty = all 'room'
    walkable: tuple[tuple[int, int, int, int, str], ...] = ()  # x, y, w, h tiles, packed sub-tiles (levels/model.py)
    visited: tuple[int, ...] = ()  # per room: ever loaded 0/1; empty = unshaded
    live: tuple[int, int] | None = None  # (pid, player path address): the position's source (hud/live.py)
    whole: bool = False  # draw the whole level however small, not the part around the player

    def to_payload(self) -> dict:
        return {
            'map': {
                'rooms': [list(room) for room in self.rooms],
                'player': list(self.player),
                'pois': [[p.label, p.kind, p.x, p.y, *([p.path] if p.path else [])] for p in self.pois],
                'route': [list(point) for point in self.route],
                'room_kinds': list(self.room_kinds),
                'walkable': [list(grid) for grid in self.walkable],
                'visited': list(self.visited),
                'live': list(self.live) if self.live else None,
                'whole': self.whole,
            }
        }

    @classmethod
    def from_payload(cls, value) -> MapCard:
        try:
            data = value['map']
            rooms = tuple((int(x), int(y), int(w), int(h)) for x, y, w, h in data['rooms'])
            px, py = (float(v) for v in data['player'])
            pois = tuple(
                MapPoi(str(label), str(kind), float(x), float(y), *(int(path) for path in rest[:1]))
                for label, kind, x, y, *rest in data['pois']
            )
            route = tuple((float(x), float(y)) for x, y in data.get('route', ()))
            kinds = tuple(str(kind) for kind in data.get('room_kinds', ()))
            walkable = tuple((int(x), int(y), int(w), int(h), str(c)) for x, y, w, h, c in data.get('walkable', ()))
            visited = tuple(int(flag) for flag in data.get('visited', ()))
            live = data.get('live')
            live = (int(live[0]), int(live[1])) if live else None
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Invalid map payload') from exc
        return cls(rooms, (px, py), pois, route, kinds, walkable, visited, live, bool(data.get('whole', False)))


def project(x: float, y: float) -> tuple[float, float]:
    return x - y, (x + y) / 2


def fit(
    card: MapCard, width: float, height: float, *, margin: float = 10, min_scale: float = 0.0, local_scale: float = 0.0
):
    """Map-plane (x, y) → pixel transform that fits every room corner, the player and the level's
    own dots in the box. Monster dots do not count: one with a wrong position must not shrink the map.

    A level that would be drawn below `min_scale` (pixels per projected unit) is drawn at
    `local_scale` instead (at least `min_scale`), with the player in the middle; the view stops
    at the level's edge, so the card never shows more empty space than the fitted map would.
    `card.whole` keeps the whole level."""
    return _layout(card, width, height, margin, min_scale, local_scale)[0]


def _layout(card: MapCard, width, height, margin, min_scale, local_scale):
    """(transform, local): `fit`'s transform and whether it is the view around the player."""
    points = [(x + dx, y + dy) for x, y, w, h in card.rooms for dx in (0, w) for dy in (0, h)]
    points += [card.player, *((p.x, p.y) for p in card.pois if p.kind not in MONSTER_KINDS)]
    projected = [project(x, y) for x, y in points]
    min_x, max_x = min(p[0] for p in projected), max(p[0] for p in projected)
    min_y, max_y = min(p[1] for p in projected), max(p[1] for p in projected)
    scale = min((width - 2 * margin) / max(max_x - min_x, 1e-9), (height - 2 * margin) / max(max_y - min_y, 1e-9))
    local = scale < min_scale and not card.whole
    if local:
        scale = max(min_scale, local_scale)
    player_x, player_y = project(*card.player)

    def offset(size: float, low: float, high: float, player: float) -> float:
        extent = (high - low) * scale
        if extent <= size - 2 * margin + 1e-9:
            return (size - extent) / 2
        return min(margin, max(size - margin - extent, size / 2 - (player - low) * scale))

    offset_x = offset(width, min_x, max_x, player_x)
    offset_y = offset(height, min_y, max_y, player_y)

    def transform(x: float, y: float) -> tuple[float, float]:
        sx, sy = project(x, y)
        return offset_x + (sx - min_x) * scale, offset_y + (sy - min_y) * scale

    return transform, local


def pin(origin, point, width: float, height: float, inset: float = PIN_INSET):
    """(x, y, pinned): `point`, or where the line to it from `origin` (inside the box) leaves the
    box shrunk by `inset`."""
    (ox, oy), (x, y) = origin, point
    if inset <= x <= width - inset and inset <= y <= height - inset:
        return x, y, False
    reach = 1.0
    for start, end, size in ((ox, x, width), (oy, y, height)):
        if end > size - inset:
            reach = min(reach, (size - inset - start) / (end - start))
        elif end < inset:
            reach = min(reach, (inset - start) / (end - start))
    reach = max(reach, 0.0)
    return ox + (x - ox) * reach, oy + (y - oy) * reach, True


def _arrowhead(cr, x, y, angle, colour, length=13.0, half_width=6.0):
    """A triangle with its tip at (x, y), pointing along `angle`."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.move_to(0, 0)
    cr.line_to(-length, -half_width)
    cr.line_to(-length, half_width)
    cr.close_path()
    cr.restore()
    cr.set_source_rgba(*colour, 1)
    cr.fill_preserve()
    cr.set_source_rgba(0.1, 0.1, 0.1, 1)
    cr.set_line_width(1.5)
    cr.stroke()


def _outside(corners, width, height) -> bool:
    return (
        all(x < 0 for x, _ in corners)
        or all(x > width for x, _ in corners)
        or all(y < 0 for _, y in corners)
        or all(y > height for _, y in corners)
    )


def _dot(cr, x, y, radius, fill, ring):
    cr.arc(x, y, radius, 0, 2 * math.pi)
    cr.set_source_rgba(*fill, 1)
    cr.fill_preserve()
    cr.set_source_rgba(*ring, 1)
    cr.set_line_width(1.5)
    cr.stroke()


FLOOR = (0.80, 0.72, 0.52, 0.80)
WALKABLE_RUN = re.compile('1+')


def _draw_tiles(cr, transform, x, y, w, h, cells, floor=FLOOR):
    """One iso parallelogram per run of walkable sub-tiles in a row, the room filled in one go
    (no seams between rows); rock is left transparent."""
    columns = w * TILE_UNITS
    bits = unpack_cells(cells, columns * h * TILE_UNITS)
    if bits is None:
        return
    for row in range(h * TILE_UNITS):
        top, bottom = y + row / TILE_UNITS, y + (row + 1) / TILE_UNITS
        for run in WALKABLE_RUN.finditer(bits[row * columns : (row + 1) * columns]):
            left, right = x + run.start() / TILE_UNITS, x + run.end() / TILE_UNITS
            cr.move_to(*transform(left, top))
            cr.line_to(*transform(right, top))
            cr.line_to(*transform(right, bottom))
            cr.line_to(*transform(left, bottom))
            cr.close_path()
    cr.set_source_rgba(*floor)
    cr.fill()


def draw_map(cr, width: float, height: float, card: MapCard, *, min_scale: float = 0.0, local_scale: float = 0.0):
    """No background (user, 2026-09-30): the game shows around the level and through rock.
    `min_scale`, `local_scale`: see `fit`; what falls outside the card is not drawn."""
    if not card.rooms:
        return
    transform, local = _layout(card, width, height, 10, min_scale, local_scale)
    alpha = LOCAL_ALPHA if local else 1.0
    cr.save()
    cr.rectangle(0, 0, width, height)
    cr.clip()
    cr.set_line_width(1)
    walled = {(x, y, w, h) for x, y, w, h, _ in card.walkable}
    visited = dict(zip(card.rooms, card.visited, strict=True)) if len(card.visited) == len(card.rooms) else {}

    def corners_of(x, y, w, h):
        return [transform(x, y), transform(x + w, y), transform(x + w, y + h), transform(x, y + h)]

    for index, (x, y, w, h) in enumerate(card.rooms):
        if (x, y, w, h) in walled:
            continue  # its walkable tiles are drawn instead; rock stays transparent
        corners = corners_of(x, y, w, h)
        if _outside(corners, width, height):
            continue
        kind = card.room_kinds[index] if index < len(card.room_kinds) else 'room'
        fill, outline = ROOM_STYLES.get(kind, ROOM_STYLES['room'])
        fill = room_fill(fill, bool(visited.get((x, y, w, h), 1)), alpha)
        cr.move_to(*corners[0])
        for corner in corners[1:]:
            cr.line_to(*corner)
        cr.close_path()
        cr.set_source_rgba(*fill)
        cr.fill_preserve()
        cr.set_source_rgba(*outline[:3], outline[3] * alpha)
        cr.stroke()
    for x, y, w, h, cells in card.walkable:
        if not _outside(corners_of(x, y, w, h), width, height):
            _draw_tiles(cr, transform, x, y, w, h, cells, room_fill(FLOOR, bool(visited.get((x, y, w, h), 1)), alpha))
    if len(card.route) >= 2:
        cr.move_to(*transform(*card.route[0]))
        for point in card.route[1:]:
            cr.line_to(*transform(*point))
        cr.set_source_rgba(0.95, 0.95, 0.95, 0.85)
        cr.set_line_width(2)
        cr.set_dash([4, 3])
        cr.stroke()
        cr.set_dash([])
    player = transform(*card.player)
    # Monsters under the level's POIs, so a pack never hides the way on.
    under = {kind: index for index, kind in enumerate(MONSTER_ORDER)}
    for poi in sorted(card.pois, key=lambda poi: under.get(poi.kind, len(under))):
        if poi.kind == 'pack':
            continue
        colour = KIND_COLOURS.get(poi.kind, KIND_COLOURS['target'])
        radius = KIND_RADII.get(poi.kind, POI_RADIUS)
        x, y = transform(poi.x, poi.y)
        if poi.kind in MONSTER_KINDS:
            pinned = False  # a monster out of the card is not this card's business
        else:
            x, y, pinned = pin(player, (x, y), width, height)
        if pinned:
            _arrowhead(cr, x, y, math.atan2(y - player[1], x - player[0]), colour)
        elif poi.kind == 'elite':
            cr.arc(x, y, radius + ELITE_RING / 2, 0, 2 * math.pi)
            cr.set_source_rgba(*KIND_COLOURS['danger'], 1)
            cr.fill()
            cr.arc(x, y, radius - ELITE_RING / 2, 0, 2 * math.pi)
            cr.set_source_rgba(*colour, 1)
            cr.fill()
        elif radius < POI_RADIUS:
            cr.arc(x, y, radius, 0, 2 * math.pi)
            cr.set_source_rgba(*colour, 1)
            cr.fill()
        else:
            _dot(cr, x, y, radius, colour, (0.1, 0.1, 0.1))
    _dot(cr, *player, 4.5, (1, 1, 1), (0.85, 0.2, 0.2))
    cr.restore()
