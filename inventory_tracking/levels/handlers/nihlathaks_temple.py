"""Nihlathak's Temple: Pindleskin, where the Temple Entrance's one DS1 file places him (terror/data/elites.json preset
1088: (58, 35) units, beside the stairs down to the Halls of Anguish, warp slot 1 at (12, 6.5) tiles). Its stairs and
Anya's red portal are the generic ways out (levels/exits.py). Unconfirmed: no fixture yet (2026-10-20, for the act 5
shard's walk up from the Halls of Pain; routes/catalog/act5.py 'Halls of Anguish').
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target("Nihlathak's Temple", areas={121}, label='Pindleskin', preset=r'Act 5 - Temple Entrance', boss='Pindleskin'),
]
