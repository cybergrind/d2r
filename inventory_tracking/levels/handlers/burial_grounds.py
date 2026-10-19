"""Burial Grounds: the graveyard preset (Blood Raven and both crypt doors) and the way back."""

from inventory_tracking.levels.handler import Exit, ExitsHandler, PoiSpec


HANDLERS = [
    ExitsHandler(
        'Burial Grounds',
        frozenset({17}),
        (PoiSpec('Graveyard', r'Act 1 - Graveyard'),),
        exits=(Exit(3, 'Cold Plains', 'previous'),),
    )
]
