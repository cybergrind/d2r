"""Act 5 ice mazes: 'Ice Next' (levels.json Vis1) the level ahead, 'Ice Down' (Vis2) the side cave."""

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
