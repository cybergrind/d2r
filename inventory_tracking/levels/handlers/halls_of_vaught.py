"""Halls of Vaught: Nihlathak, placed by the level's layout variant.

The whole level is one 84x84 preset, 'Act 5 - Temple Final Room', in four DS1 variants
(lvlprest File1..4: NihlE, NihlN, NihlS, NihlW); the player enters at its centre. The
variant index is read from the preset object (dump 20260930T082410Z-54658110: 3 = NihlW).
The letter names the side Nihlathak is on. Confirmed 2026-09-30: the user saw him west and north
in two games; the NihlW game rules out "the side the layout opens to", which would be east.
Game 3 (NihlE, dump 20260930T144010Z-ca3068d4) saw Nihlathak himself at 94% across the preset,
mid-height: the marker sits 6% inside the edge (the generic 15% left it 40 units short, so a
Win+C next to him pointed back). The four layouts mirror each other; only NihlE is measured.
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target(
        'Halls of Vaught',
        areas={124},
        label='Nihlathak',
        preset=r'Act 5 - Temple Final Room',
        sides=('E', 'N', 'S', 'W'),
        inset=0.06,
        confirmed=True,
    )
]
