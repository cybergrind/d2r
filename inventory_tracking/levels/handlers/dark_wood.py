"""Dark Wood: the Underground Passage and the border gap to Black Marsh.

Unconfirmed (2026-09-30). The level's only warp is the Underground Passage (d2data levels): a cave
entrance, plain or in a cliff, as in Cold Plains and Stony Field (D2MOO DrlgOutWild); evidence
20260930T120851 had 'Wild Cliff Cave Left'. Its only border link is Black Marsh (D2MOO
DrlgOutPlace), so its one gap is named by elimination when the far side isn't read yet.
The Tree of Inifuss ('Act 1 - Inifus') is not marked.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Dark Wood',
        frozenset({5}),
        (PoiSpec('Underground Passage', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),),
        exits=(Exit(6, 'Black Marsh'),),
    )
]
