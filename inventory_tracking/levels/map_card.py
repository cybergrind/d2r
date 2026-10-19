"""The level map card's data: the rooms, the player and the dots it shows, as the HUD's payload carries them (drawn by
hud/map.py). No drawing here: levels/ and terror/ build cards without the UI."""

from dataclasses import dataclass

from inventory_tracking.presentation import Tone


__all__ = ['KIND_TONES', 'MapCard', 'MapPoi']

# One colour per POI kind for rows, arrows and dots (user, 2026-09-30); unknown kinds use the POI colour.
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


@dataclass(frozen=True)
class MapPoi:
    label: str
    kind: str
    x: float
    y: float
    path: int = 0  # address of a monster's dynamic path, when the HUD can follow it (hud/live.py)
    unit: int = 0  # a monster's unit record, read every frame by hud/live.py `LiveDots`
    uid: int = 0

    def row(self) -> list:
        """The payload row: [label, kind, x, y], plus the path address, unit address and id when known."""
        tail = [self.path, self.unit, self.uid] if self.unit else [self.path] if self.path else []
        return [self.label, self.kind, self.x, self.y, *tail]


@dataclass(frozen=True)
class MapCard:
    rooms: tuple[tuple[int, int, int, int], ...]  # x, y, width, height in tiles
    player: tuple[float, float]
    pois: tuple[MapPoi, ...] = ()
    route: tuple[tuple[float, float], ...] = ()  # player → teleport hops → POI, in tiles
    room_kinds: tuple[str, ...] = ()  # per room: 'room' or 'edge' (outdoor level border); empty = all 'room'
    walkable: tuple[tuple[int, int, int, int, str], ...] = ()  # x, y, w, h tiles, packed sub-tiles (levels/model.py)
    visited: tuple[int, ...] = ()  # per room: ever loaded 0/1; empty = unshaded
    live: tuple[int, int] | None = None  # (pid, player path address): the position's source (hud/live.py)
    whole: bool = False  # draw the whole level however small, not the part around the player
    units: tuple[int, int] | None = None  # (unit table, area): the HUD walks it for undotted monsters (hud/live.py)

    def to_payload(self) -> dict:
        return {
            'map': {
                'rooms': [list(room) for room in self.rooms],
                'player': list(self.player),
                'pois': [p.row() for p in self.pois],
                'route': [list(point) for point in self.route],
                'room_kinds': list(self.room_kinds),
                'walkable': [list(grid) for grid in self.walkable],
                'visited': list(self.visited),
                'live': list(self.live) if self.live else None,
                'whole': self.whole,
                'units': list(self.units) if self.units else None,
            }
        }

    @classmethod
    def from_payload(cls, value) -> MapCard:
        try:
            data = value['map']
            rooms = tuple((int(x), int(y), int(w), int(h)) for x, y, w, h in data['rooms'])
            px, py = (float(v) for v in data['player'])
            pois = tuple(
                MapPoi(str(label), str(kind), float(x), float(y), *(int(value) for value in rest[:3]))
                for label, kind, x, y, *rest in data['pois']
            )
            route = tuple((float(x), float(y)) for x, y in data.get('route', ()))
            kinds = tuple(str(kind) for kind in data.get('room_kinds', ()))
            walkable = tuple((int(x), int(y), int(w), int(h), str(c)) for x, y, w, h, c in data.get('walkable', ()))
            visited = tuple(int(flag) for flag in data.get('visited', ()))
            live = data.get('live')
            live = (int(live[0]), int(live[1])) if live else None
            units = data.get('units')
            units = (int(units[0]), int(units[1])) if units else None
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Invalid map payload') from exc
        whole = bool(data.get('whole', False))
        return cls(rooms, (px, py), pois, route, kinds, walkable, visited, live, whole, units)
