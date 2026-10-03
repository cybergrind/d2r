"""Blood Moor: the Den of Evil and the border gaps to Cold Plains and the Rogue Encampment.

Unconfirmed (D2MOO DrlgOutWild/DrlgOutPlace, 2026-10-01; no evidence yet). The Den's mouth is the
'Act 1 - DOE Entrance' preset (Cave Entrance + 1, spawned only in the Blood Moor). The exits
are open Act 1 border gaps (handler.ExitsHandler), named when the level behind them is read.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Blood Moor',
        frozenset({2}),
        (PoiSpec('Den of Evil', r'Act 1 - DOE Entrance', 'stairs'),),
        exits=(Exit(3, 'Cold Plains'), Exit(1, 'Rogue Encampment', 'previous')),
    )
]
