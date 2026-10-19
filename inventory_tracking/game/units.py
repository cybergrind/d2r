"""A unit table walked once for a look (cleanup A4, rca/2026-10-19/cleanup/town-items-world.md): the readers of one
look share the walk's rows instead of walking the table again each (`GameMemory.loot` walked the item table six
times and the player table twice up to 2026-10-19).

A walk reads the table's 128 bucket heads of the unit type, then every chain (native/units.py `walk_units`: its
rows, the errors it met and whether it is whole).
"""

import struct

from inventory_tracking.native.units import walk_units


def walked(read, table: int, unit_type: int, *, records: bool = False) -> dict:
    """`walk_units` of the unit table at `table` for `unit_type`; OSError/ValueError when its heads are unread."""
    heads = struct.unpack('<128Q', read(table + unit_type * 1024, 1024))
    return walk_units(read, heads, unit_type, records=records)
