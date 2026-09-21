"""Optional item-label state read, called only after LiveReader's build gate."""

import os
import time

from .image_probe import read_mappings
from .layout import SHOW_ITEMS_RVA
from .linux_process import identity, process_mappings
from .models import Observation


def observe_show_items(pid, images) -> Observation[bool]:
    """Read twice with process/mapping checks; failures suppress only this warning."""
    sampled = time.monotonic()
    try:
        token = images['identity']
        address = images['candidate_base'] + SHOW_ITEMS_RVA
        if identity(pid) != token:
            raise ValueError('Show Items process changed')
        before = read_mappings(process_mappings(pid), address, 1)
        if not before or not all(m[3].startswith('r') for m in before):
            raise ValueError('Show Items byte is unreadable')
        fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        try:
            value = os.pread(fd, 1, address)
            if value not in (b'\x00', b'\x01'):
                raise ValueError('Invalid Show Items byte')
            if os.pread(fd, 1, address) != value:
                raise ValueError('Show Items changed during read')
        finally:
            os.close(fd)
        if identity(pid) != token or read_mappings(process_mappings(pid), address, 1) != before:
            raise ValueError('Show Items process/mappings changed')
        return Observation(sampled, value == b'\x01')
    except (OSError, ValueError) as exc:
        return Observation.unavailable(sampled, str(exc))
