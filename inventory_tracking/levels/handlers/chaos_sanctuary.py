"""Chaos Sanctuary: Diablo's star, so teleport steps rush to it (user, 2026-10-10), and the seals.

The star is the `DiabloStart` object of the 'Diablo Heart' preset (heart.ds1). Unconfirmed.
"""

from inventory_tracking.levels.handler import PoiSpec, target
from inventory_tracking.levels.model import SEALS


DIABLO_START = (53, 53)
# In the order the routes open them (routes.md): Vizier, De Seis, Infector.
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
