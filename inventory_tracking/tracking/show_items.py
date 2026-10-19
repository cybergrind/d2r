"""Optional item-label state read, called only after LiveReader's build gate."""

import time

from inventory_tracking.models import Observation
from inventory_tracking.native.layout import SHOW_ITEMS_RVA
from inventory_tracking.native.memory import stable_read


def decode_show_items(value: bytes) -> bool:
    if value not in (b'\x00', b'\x01'):
        raise ValueError('Invalid Show Items byte')
    return value == b'\x01'


def observe_show_items(pid, images) -> Observation[bool]:
    """Read twice with process/mapping checks; failures suppress only this warning."""
    sampled = time.monotonic()
    try:
        address = images['candidate_base'] + SHOW_ITEMS_RVA
        shown = stable_read(
            pid, images, address, 1, decode_show_items, name='Show Items', unreadable='Show Items byte is unreadable'
        )
        return Observation(sampled, shown)
    except (OSError, ValueError) as exc:
        return Observation.unavailable(sampled, str(exc))
