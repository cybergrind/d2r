"""Blood Moor: the Den of Evil, the border gap to Cold Plains and the way back to the Rogue Encampment.

Unconfirmed (D2MOO DrlgOutWild/DrlgOutPlace, 2026-10-01; no evidence yet). The Den's mouth is the
'Act 1 - DOE Entrance' preset (Cave Entrance + 1, spawned only in the Blood Moor). The exits
are open Act 1 border gaps (handler.ExitsHandler), named when the level behind them is read.

2026-10-06, from nine evidence entries: the level has one open gap, to Cold Plains (so it is named
by elimination); the Rogue Encampment side is the 'Town 1 Transition' preset (E in seven of nine),
not a gap. With the camp listed as a gap the Cold Plains one stayed a plain 'Exit' in seven.
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
