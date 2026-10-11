"""Chaos Sanctuary: Diablo's star, so teleport steps rush to it (user, 2026-10-10 night).

The Sanctuary is five 24x24 presets: 'Diablo Entry', the arms W, E and N with the seals, and
'Diablo Heart' in the middle. The Heart has one layout (act4/diab/heart.ds1, read from the install
2026-10-10), which places the object `DiabloStart` at (53, 53) units from the preset's origin: the
star Diablo rises from. Unconfirmed: the level has no dump yet.
"""

from inventory_tracking.levels.handler import target


DIABLO_START = (53, 53)

HANDLERS = [
    target('Chaos Sanctuary', areas={108}, label='Diablo', preset=r'Act 4 - Diablo Heart', at=DIABLO_START),
]
