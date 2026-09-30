"""Open-panel flags (inventory, stash, cube, shop…) read like the Show Items byte.

One bounded read of the flag array after the build gate; every byte must be 0 or 1
and the array must read identically twice, otherwise the observation is unavailable.
"""

import os
import time

from inventory_tracking.models import Observation
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.layout import PANEL_FLAGS, UI_PANELS_RVA, UI_PANELS_SIZE
from inventory_tracking.native.process import identity, process_mappings


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
        token = images['identity']
        address = images['candidate_base'] + UI_PANELS_RVA
        if identity(pid) != token:
            raise ValueError('Panel flags process changed')
        before = read_mappings(process_mappings(pid), address, UI_PANELS_SIZE)
        if not before or not all(m[3].startswith('r') for m in before):
            raise ValueError('Panel flags are unreadable')
        fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        try:
            raw = os.pread(fd, UI_PANELS_SIZE, address)
            panels = decode_panels(raw)
            if os.pread(fd, UI_PANELS_SIZE, address) != raw:
                raise ValueError('Panel flags changed during read')
        finally:
            os.close(fd)
        if identity(pid) != token or read_mappings(process_mappings(pid), address, UI_PANELS_SIZE) != before:
            raise ValueError('Panel flags process/mappings changed')
        return Observation(sampled, panels)
    except (OSError, ValueError) as exc:
        return Observation.unavailable(sampled, str(exc))
