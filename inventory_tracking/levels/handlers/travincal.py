"""Travincal: the Durance of Hate entrance (the 'Travincal N' room, so room-level) and the Council."""

from inventory_tracking.levels.handler import PoiSpec, target


HANDLERS = [
    target(
        'Travincal',
        areas={83},
        label='Durance of Hate',
        preset=r'Act 3 - Travincal N',
        kind='stairs',
        # The other two councillors stand within 11 units of him (terror/data/elites.json).
        extra=[PoiSpec('Council', r'Act 3 - Travincal N', boss='Ismail Vilehand')],
    )
]
