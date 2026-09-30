"""Outer Steppes: the gap to the Plains of Despair and the way back to the Pandemonium Fortress.

Unconfirmed (from D2MOO DrlgOutdoors/DrlgOutPlace and d2data, 2026-10-01; no evidence yet). The
level has no waypoint. The Fortress side is one 'Act 4 - Fortress Transition' preset (8x24,
spawned in Outer Steppes by the 0x400000/0x800000 outdoor flags). Level links are Act 4 border
gaps: 'Mesa Border 1-4' in the open DS1 file (Border*o.ds1 = file 3; there is no 'oe' file).
Its only gap leads to the Plains of Despair, so an unread gap is named by elimination.
"""

from inventory_tracking.levels.handler import ACT4_GAP, Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Outer Steppes',
        frozenset({104}),
        (PoiSpec('Pandemonium Fortress', r'Act 4 - Fortress Transition', 'previous'),),
        exits=(Exit(105, 'Plains of Despair'),),
        gap=ACT4_GAP,
        gap_variants=(3,),
    )
]
