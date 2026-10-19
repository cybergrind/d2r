"""Stony Field: the Tristram portal first (user, 2026-10-12), the Underground Passage, the way back.

The portal and Wirt's body are objects the step clicks (`use`); the body is the WIRT object
Tri_Town4.ds1 places (objpreset 103). Unconfirmed.
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
