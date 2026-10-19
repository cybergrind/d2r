"""Plains of Despair: Izual, the gap to the City of the Damned and the gap back to Outer Steppes."""

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
