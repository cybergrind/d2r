"""Inner Cloister → Cathedral → Catacombs 1: the doorway on, the waypoint, the stairs down and the ways back.

Each level is one fixed preset (levels.txt DrlgType 2): Inner Cloister 'Act 1 - Courtyard 2' (lvlprest 256,
Cat_Court.ds1), Cathedral 'Act 1 - Cathedral' (257, Cathy3.ds1), the Cathedral placed by Depend 32 at the Cloister's
north edge. Inner Cloister ↔ Cathedral has no warp (levels.txt 32 Warp1 and 33 Warp0 = -1): an open passage through
the Cathedral's doorway, walked (levels/exits.py `through`). The Cloister's one warp is the way back to Jail 3 (Warp0
'Act 1 Jail Down'), the Cathedral's the stairs to Catacombs 1 (Warp1 'Act 1 Cathedral To Catacombs'); both from
data/preset_warps.json, as is the Cloister's waypoint. Unconfirmed: no level run has crossed by these marks yet.
"""

import re
from dataclasses import dataclass, replace

from inventory_tracking.levels.handler import Handler, PoiSpec, instances, marker_room
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Poi
from inventory_tracking.levels.presets import PRESET_NAMES, preset_name, warp_spots, waypoint_spot
from inventory_tracking.native.layout import TILE_UNITS


INNER_CLOISTER, CATHEDRAL = 32, 33
COURTYARD, NAVE = 'Act 1 - Courtyard 2', 'Act 1 - Cathedral'
# The doorway's tile from each preset's origin. The Cloister's north wall row (y 1000) is walkable only at sub-tiles
# 20048-20053 (tile x 4009.6-4010.8) in every take of the level; the walk from the Cathedral crossed there, at
# (20052.9, 5000.1) → (20052.5, 5000.5) (takes 20261017T210206Z-33 → 20261017T210235Z-32).
# Preset origins: (4000, 1000) and (3996, 966).
CLOISTER_DOORWAY = (10.5, 0.5)
NAVE_DOORWAY = (14.5, 33.5)


def preset_def(name: str) -> int:
    (found,) = [preset for preset, known in PRESET_NAMES.items() if known == name]
    return found


def warp_at(name: str, slot: int) -> tuple[float, float]:
    """World units from the preset origin of its one layout's warp `slot` (levels.txt Vis slot)."""
    x, y = warp_spots(preset_def(name), 0)[slot]
    return x * TILE_UNITS, y * TILE_UNITS


def waypoint_at(name: str) -> tuple[float, float]:
    spot = waypoint_spot(preset_def(name), 0)
    assert spot is not None, name
    return spot[0] * TILE_UNITS, spot[1] * TILE_UNITS


@dataclass(frozen=True)
class Doorway(Handler):
    """A one-preset level with an open passage at a fixed tile of its preset: marked as a way out naming the level
    it leads into, first when it is the way on ('stairs'), last when it is the way back ('previous')."""

    preset: str = ''
    passage: str = ''
    into: int = 0
    kind: str = 'stairs'
    at: tuple[float, float] = (0.0, 0.0)  # tiles from the preset origin

    def labels(self) -> frozenset[str]:
        return super().labels() | {self.passage}

    def guide(self, snapshot: LevelSnapshot) -> Guidance:
        guidance = super().guide(snapshot)
        named = (room for room in snapshot.rooms if re.fullmatch(self.preset, preset_name(room.preset)))
        found = [room for room, _ in instances(named)]
        if len(found) != 1:
            return replace(guidance, problems=(*guidance.problems, f'{self.passage}: {len(found)} presets match'))
        room = found[0]
        x0, y0, *_ = room.block or (room.x, room.y)
        spot = (x0 + self.at[0], y0 + self.at[1])
        # No layout on the mark's room: spots.pinpoint would move a way out of a one-warp preset onto that warp (the
        # Jail stairs, the Catacombs stairs), and this mark is the doorway, not the warp.
        mark = replace(marker_room(room, *spot), variant=None)
        poi = Poi(self.passage, mark, self.kind, spot, self.into)
        pois = (poi, *guidance.pois) if self.kind == 'stairs' else (*guidance.pois, poi)
        return replace(guidance, pois=pois)


HANDLERS = [
    Doorway(
        'Inner Cloister',
        frozenset({INNER_CLOISTER}),
        (
            PoiSpec('Waypoint', re.escape(COURTYARD), 'waypoint', optional=True, at=waypoint_at(COURTYARD)),
            PoiSpec('Jail 3', re.escape(COURTYARD), 'previous', at=warp_at(COURTYARD, 0)),
        ),
        preset=re.escape(COURTYARD),
        passage='Cathedral',
        into=CATHEDRAL,
        at=CLOISTER_DOORWAY,
    ),
    Doorway(
        'Cathedral',
        frozenset({CATHEDRAL}),
        (PoiSpec('Catacombs 1', re.escape(NAVE), 'stairs', at=warp_at(NAVE, 1)),),
        preset=re.escape(NAVE),
        passage='Inner Cloister',
        into=INNER_CLOISTER,
        kind='previous',
        at=NAVE_DOORWAY,
    ),
]
