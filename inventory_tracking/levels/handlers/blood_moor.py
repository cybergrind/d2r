"""Blood Moor: the Den of Evil, the gap to Cold Plains and the way back to the Rogue Encampment.

The camp side is the 'Town 1 Transition' preset, not a gap (nine evidence entries, 2026-10-06).
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Blood Moor',
        frozenset({2}),
        (
            PoiSpec('Den of Evil', r'Act 1 - DOE Entrance', 'stairs'),
            PoiSpec('Rogue Encampment', r'Act 1 - Town 1 Transition [ES]', 'previous', optional=True),
        ),
        exits=(Exit(3, 'Cold Plains'),),
    )
]
