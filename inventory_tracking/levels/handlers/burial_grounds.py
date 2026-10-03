"""Burial Grounds: the graveyard (Blood Raven, the Crypt and the Mausoleum) and the way back.

Unconfirmed (D2MOO DrlgOutWild, 2026-10-01; no evidence yet). The level spawns one fixed 24x32
'Act 1 - Graveyard' preset holding both crypt entrances; the arrow is to the preset, not to a
single door. The only link is Cold Plains, an open border gap (Burial Grounds uses file 4).
"""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Burial Grounds',
        frozenset({17}),
        (PoiSpec('Graveyard', r'Act 1 - Graveyard'),),
        exits=(Exit(3, 'Cold Plains', 'previous'),),
    )
]
