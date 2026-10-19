"""Outer Steppes: the gap to the Plains of Despair and the way back to the Pandemonium Fortress.

Act 4 border gaps are 'Mesa Border 1-4' file 3 (Border*o.ds1; D2MOO DrlgOutPlace).
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
