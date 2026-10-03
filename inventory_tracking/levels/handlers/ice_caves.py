"""Crystalline Passage and Glacial Trail: the level ahead, the side cave, the waypoint and the way back.

Unconfirmed (from d2data levels/lvlprest, 2026-10-01; no evidence yet). Both are 'Act 5 - Ice'
mazes of 16x16 presets. levels.json: Vis0 is the way back, Vis1 (Warp 74, 'Ice Next') the level
ahead and Vis2 (Warp 75, 'Ice Down') the side cave: Frozen River (114, Anya) off Crystalline
Passage (113), Drifter Cavern (116) off Glacial Trail (115). Both place 'Ice waypoint …'. The
side caves are single fixed presets ('Ice River A/B', 'Ice Pool A/B'): no handler.
Ancients' Way (118, Glacial Caves 1; 2026-10-01, same DRLGMAZE_PlaceAct5IceStuff) places 'Ice
Next' (Arreat Summit), 'Ice Down' (the Icy Cellar), 'Ice waypoint' and 'Ice Prev'.
"""

from inventory_tracking.levels.handler import Handler, PoiSpec, previous, waypoint


ICE = 'Act 5 - Ice'


def ahead(label: str) -> PoiSpec:
    return PoiSpec(label, rf'{ICE} Next [NSEW]', 'stairs', family=ICE)


def side_cave(label: str, kind: str) -> PoiSpec:
    return PoiSpec(label, rf'{ICE} Down [NSEW]', kind, family=ICE, warp=True)


HANDLERS = [
    Handler(
        'Crystalline Passage',
        frozenset({113}),
        (
            ahead('Glacial Trail'),
            side_cave('Frozen River', 'target'),  # Anya
            waypoint(ICE),
            previous(ICE, 'Arreat Plateau'),
        ),
    ),
    Handler(
        'Glacial Trail',
        frozenset({115}),
        (
            ahead('Frozen Tundra'),
            side_cave('Drifter Cavern', 'stairs'),
            waypoint(ICE),
            previous(ICE, 'Crystalline Passage'),
        ),
    ),
    Handler(
        "Ancients' Way",
        frozenset({118}),
        (ahead('Arreat Summit'), side_cave('Icy Cellar', 'stairs'), waypoint(ICE), previous(ICE, 'Frozen Tundra')),
    ),
]
