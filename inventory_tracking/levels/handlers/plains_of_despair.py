"""Plains of Despair: Izual, the gap to the City of the Damned and the way back to Outer Steppes.

Unconfirmed (from D2MOO DrlgOutdoors/DrlgOutPlace and d2data, 2026-10-01; no evidence yet). No
waypoint. Izual's spot is one 'Act 4 - Mesa 2 Izual' preset (8x8, spawned only in this level).
Both level links are open Act 4 border gaps ('Mesa Border 1-4', file 3), named by the level
behind them once read, the last unknown one by elimination.
"""

from inventory_tracking.levels.handler import ACT4_GAP, Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Plains of Despair',
        frozenset({105}),
        (PoiSpec('Izual', r'Act 4 - Mesa 2 Izual'),),
        exits=(Exit(106, 'City of the Damned'), Exit(104, 'Outer Steppes', 'previous')),
        gap=ACT4_GAP,
        gap_variants=(3,),
    )
]
