"""Stony Field: the Tristram portal (Cairn Stones), the Underground Passage and the way back.

Unconfirmed (from d2data/D2MOO, 2026-09-30; no evidence yet). The portal to Tristram opens at the
Cairn Stones, one preset ('Act 1 - Cairn Stones'). The level's only warp is the Underground
Passage: a cave entrance, plain or in a cliff, as in Cold Plains and Tamoe (D2MOO DrlgOutWild).
Its only border link is Cold Plains (D2MOO DrlgOutPlace: Stony Field and Dark Wood are in
separate link groups), so its one gap is named by elimination when the far side isn't read yet.
The Cairn Stones are the level's first mark (user, 2026-10-12): the next level here is Tristram, so
the teleport step runs Stony Field -> Tristram -> Wirt's body. The way in is a portal object the
game puts among the stones, not a warp tile, so the mark names the object (`use`) and the step clicks the
one it finds there (macros/teleport.py `use_thing`).

Tristram is one preset ('Act 1 - Tristram', Tri_Town4.ds1) covering the whole level, so the preset
gives no direction. The mark is where the file places the WIRT object (objpreset Index 103, read
from the install on 2026-10-12): (48, 179) units from the preset origin, in the south-west corner.
The body is clicked the same way (user, 2026-10-12): it drops Wirt's Leg and gold.
Unconfirmed: no evidence of the level yet.
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec, target
from inventory_tracking.levels.model import PORTAL, WIRTS_BODY


HANDLERS = [
    ExitsHandler(
        'Stony Field',
        frozenset({4}),
        (
            PoiSpec('Tristram', r'Act 1 - Cairn Stones', use=PORTAL),
            PoiSpec('Underground Passage', r'Act 1 - (Cave Entrance|Wild Cliff Cave (Left|Right))', 'stairs'),
        ),
        exits=(Exit(3, 'Cold Plains', 'previous'),),
        pois_first=True,
    ),
    target('Tristram', areas={38}, label="Wirt's body", preset=r'Act 1 - Tristram', at=(48, 179), use=WIRTS_BODY),
]
