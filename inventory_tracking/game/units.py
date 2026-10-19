"""A unit table walked once for a look, its rows shared by the look's readers
(rca/2026-10-19/cleanup/town-items-world.md)."""

import struct

from inventory_tracking.native.units import walk_units


def walked(read, table: int, unit_type: int, *, records: bool = False) -> dict:
    """`walk_units` of the unit table at `table` for `unit_type`; OSError/ValueError when its heads are unread."""
    heads = struct.unpack('<128Q', read(table + unit_type * 1024, 1024))
    return walk_units(read, heads, unit_type, records=records)
