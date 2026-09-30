"""Stony Field: the Tristram portal (Cairn Stones), the Underground Passage and the way back.

Unconfirmed (from d2data/D2MOO, 2026-09-30; no evidence yet). The portal to Tristram opens at the
Cairn Stones, one preset ('Act 1 - Cairn Stones'). The level's only warp is the Underground
Passage: a cave entrance, plain or in a cliff, as in Cold Plains and Tamoe (D2MOO DrlgOutWild).
Its only border link is Cold Plains (D2MOO DrlgOutPlace: Stony Field and Dark Wood are in
separate link groups), so its one gap is named by elimination when the far side isn't read yet.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Stony Field',
        frozenset({4}),
        (
            PoiSpec('Tristram', r'Act 1 - Cairn Stones'),
            PoiSpec('Underground Passage', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),
        ),
        exits=(Exit(3, 'Cold Plains', 'previous'),),
    )
]
