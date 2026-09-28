"""Which vendor's Trade panel is open, read only after LiveReader's build gate.

The panel flag array says a shop is open but not whose. Vendor stock is generated when
Trade opens and leaves memory when it closes (shop/README.md), so the one town vendor
with occupied shop grids is the vendor being traded with. Zero or several loaded
vendors make the observation unavailable rather than a guess.
"""

import os
import time

from inventory_tracking.collection.capture import read_owner_grids
from inventory_tracking.models import Observation, ShopPanel
from inventory_tracking.native.process import process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.shop.capture import VENDORS
from inventory_tracking.tracking.panels import observe_panels


# d2data monstats *hcIdx of the vendors with a Repair All button: Charsi, Fara, Hratli, Halbu, Larzuk.
SMITHS = frozenset((154, 178, 253, 257, 511))


def loaded_vendors(read, snapshot) -> list[int]:
    """Class IDs of stable vendor units with at least one occupied shop grid cell."""
    loaded = []
    for unit in snapshot.get('groups', {}).get('monsters', {}).get('units', []):
        if unit.get('txt_id') not in VENDORS or not unit.get('identity_stable'):
            continue
        grids = read_owner_grids(read, unit)
        if any(pointer for grid in grids.values() for pointer in grid['cells']):
            loaded.append(unit['txt_id'])
    return loaded


def observe_shop_panel(pid, images, snapshot) -> Observation[ShopPanel]:
    """Shop flag first; only an open shop pays for the vendor grid reads."""
    panels = observe_panels(pid, images)
    sampled = panels.sampled_at
    if panels.value is None:
        return Observation.unavailable(sampled, panels.reason)
    if not panels.value['npc_shop']:
        return Observation(sampled, ShopPanel(False))
    try:
        fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        try:
            loaded = loaded_vendors(ResearchReader(fd, process_mappings(pid)).read, snapshot)
        finally:
            os.close(fd)
        if len(loaded) != 1:
            raise ValueError('No loaded vendor stock' if not loaded else 'Several vendors have loaded stock')
        after = observe_panels(pid, images)
        if after.value is None or not after.value['npc_shop']:
            raise ValueError('Shop closed during read')
        return Observation(sampled, ShopPanel(True, VENDORS[loaded[0]], loaded[0] in SMITHS))
    except (OSError, ValueError) as exc:
        return Observation.unavailable(time.monotonic(), str(exc))
