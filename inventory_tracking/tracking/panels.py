"""Open-panel flags (inventory, stash, cube, shop…) read like the Show Items byte.

One bounded read of the flag array after the build gate; every byte must be 0 or 1
and the array must read identically twice, otherwise the observation is unavailable.
"""

import time

from inventory_tracking.models import Observation
from inventory_tracking.native.layout import PANEL_FLAGS, UI_PANELS_RVA, UI_PANELS_SIZE
from inventory_tracking.native.memory import stable_read


def decode_panels(raw: bytes) -> dict[str, bool]:
    """Named flags from one array read; rejects a short array or any value other than 0/1."""
    if len(raw) != UI_PANELS_SIZE:
        raise ValueError('Short panel flag read')
    if any(byte not in (0, 1) for byte in raw):
        raise ValueError('Invalid panel flag byte')
    return {name: raw[offset] == 1 for name, offset in PANEL_FLAGS.items()}


def observe_panels(pid, images) -> Observation[dict[str, bool]]:
    """Read the flag array twice with process/mapping checks; failures make it unavailable."""
    sampled = time.monotonic()
    try:
        address = images['candidate_base'] + UI_PANELS_RVA
        panels = stable_read(
            pid,
            images,
            address,
            UI_PANELS_SIZE,
            decode_panels,
            name='Panel flags',
            unreadable='Panel flags are unreadable',
        )
        return Observation(sampled, panels)
    except (OSError, ValueError) as exc:
        return Observation.unavailable(sampled, str(exc))
