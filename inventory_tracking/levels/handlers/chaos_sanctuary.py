"""Chaos Sanctuary: Diablo's star, so teleport steps rush to it (user, 2026-10-10 night).

The Sanctuary is five 24x24 presets: 'Diablo Entry', the arms W, E and N with the seals, and
'Diablo Heart' in the middle. The Heart has one layout (act4/diab/heart.ds1, read from the install
2026-10-10), which places the object `DiabloStart` at (53, 53) units from the preset's origin: the
star Diablo rises from. Unconfirmed: the level has no dump yet.
"""

from inventory_tracking.levels.handler import PoiSpec, target
from inventory_tracking.levels.model import SEALS


DIABLO_START = (53, 53)
# The five seals, where each arm's layout (two per arm) places them (routes.md, 2026-10-12), in the
# order the routes open them: the Grand Vizier's arm, Lord De Seis's, the Infector's.
SEAL_MARKS = (
    ('Vizier seal 1', 'W', SEALS[4]),
    ('Vizier seal 2', 'W', SEALS[3]),
    ('De Seis seal', 'N', SEALS[2]),
    ('Infector seal 1', 'E', SEALS[0]),
    ('Infector seal 2', 'E', SEALS[1]),
)

HANDLERS = [
    target(
        'Chaos Sanctuary',
        areas={108},
        label='Diablo',
        preset=r'Act 4 - Diablo Heart',
        at=DIABLO_START,
        extra=[PoiSpec(label, rf'Act 4 - Diablo Arm {arm}', thing=seal) for label, arm, seal in SEAL_MARKS],
    ),
]
