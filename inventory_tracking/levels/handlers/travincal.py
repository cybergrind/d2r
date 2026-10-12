"""Travincal: the Durance of Hate entrance.

Unconfirmed (D2MOO DRLGOUTPLACE_InitAct3OutdoorLevel, 2026-10-01; no evidence yet). The level is
six fixed presets: 'Travincal NW/N/NE' across the north and 'SW/S/SE' across the south. The
Durance entrance is in the temple in the north block, so the POI is the 32x32 'Travincal N'
room (the arrow is room-level, not the exact stairs). The waypoint has no preset of its own.
"""

from inventory_tracking.levels.handler import PoiSpec, target


HANDLERS = [
    target(
        'Travincal',
        areas={83},
        label='Durance of Hate',
        preset=r'Act 3 - Travincal N',
        kind='stairs',
        # Where the file places Ismail Vilehand; Geleb Flamefinger and Toorc Icefist stand 5 and 11
        # units from him (terror/data/elites.json): the routes' fight (routes.md, Phase 6).
        extra=[PoiSpec('Council', r'Act 3 - Travincal N', boss='Ismail Vilehand')],
    )
]
