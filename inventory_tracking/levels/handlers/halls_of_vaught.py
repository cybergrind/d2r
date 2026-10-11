"""Halls of Vaught: Nihlathak, placed by the level's layout variant.

The whole level is one 84x84 preset, 'Act 5 - Temple Final Room', in four DS1 variants
(lvlprest File1..4: NihlE, NihlN, NihlS, NihlW); the player enters at its centre. The
variant index is read from the preset object (dump 20260930T082410Z-54658110: 3 = NihlW).
The letter names the side Nihlathak is on. Confirmed 2026-09-30: the user saw him west and north
in two games; the NihlW game rules out "the side the layout opens to", which would be east.
Game 3 (NihlE, dump 20260930T144010Z-ca3068d4) saw Nihlathak himself at 94% across the preset,
mid-height: the marker sits 6% inside the edge (the generic 15% left it 40 units short, so a
Win+C next to him pointed back). The four layouts mirror each other; only NihlE is measured.

The mark is not his spot but a place to fight him from (user, 2026-10-11: "position our last jump
somewhere off the main mob pack, to avoid heavy damage"; the teleport step ends there, and after a
pickup or a sweep it goes back there). In the twenty takes of that day he stood in a pillared
pavilion of about 20 x 20 units with his pack, the same way round in all four layouts: from 14 west
and north of the side's spot to 6 east and south of it, himself 0.5 to 4.5 west and 3.5 to 4.5
north. East of the pavilion a strip 12 wide was empty of monsters on arrival in each layout. The
mark is 3 tiles east and 1 north of the spot: 15.5 to 19.5 units from him, footing and a clear line
to every part of the pavilion in each layout's take (the pillars do not stop a blade).
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
        stand=(3, -1),
        confirmed=True,
    )
]
