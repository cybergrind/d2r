"""City of the Damned: the stairs down to the River of Flame and the gap back; the waypoint has no preset."""

from inventory_tracking.levels.handler import ACT4_GAP, Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'City of the Damned',
        frozenset({106}),
        (PoiSpec('River of Flame', r'Act 4 - Mesa Warp', 'stairs'),),
        exits=(Exit(105, 'Plains of Despair', 'previous'),),
        gap=ACT4_GAP,
        gap_variants=(3,),
    )
]
