"""Bounded, unvalidated modifier-list evidence for selected-item gap research.

Head offsets 0x68/0x90 come from MapAssist/d2go; 0xD0 is 0x90 plus this build's +0x40 displacement. The +0xD0
chain supplies missing ED only after items.modifiers validates its owner, links and snapshot; raw diagnostics
are not decoded.
"""

import struct
from typing import Any

from inventory_tracking.native.units import read_stats


# Insight capture 20260923T202133Z/request-5 contains an additional pointer at
# +0x118. Capture it as research only; do not accept it as an owned stat list yet.
CANDIDATE_HEAD_OFFSETS = (0x68, 0x90, 0xD0, 0x118)
ROOT_HEADER_SIZE = 0x200
LIST_HEADER_SIZE = 0x60
PREVIOUS_LINK_OFFSET = 0x48
MAX_LISTS = 16


def capture_stat_candidates(read, pointer) -> dict[str, Any]:
    result: dict[str, Any] = {'validated': False, 'root_address': pointer, 'chains': []}
    try:
        root = read(pointer, ROOT_HEADER_SIZE)
        result['header_hex'] = root.hex()
        for offset in CANDIDATE_HEAD_OFFSETS:
            current = struct.unpack_from('<Q', root, offset)[0]
            chain: dict[str, Any] = {'head_offset': offset, 'complete': False, 'lists': []}
            result['chains'].append(chain)
            visited = set()
            try:
                while current:
                    if current in visited or len(visited) >= MAX_LISTS:
                        raise ValueError('Candidate list cycle or traversal bound')
                    if not 0x10000 <= current < 2**47 or current % 8:
                        raise ValueError('Invalid candidate list pointer')
                    visited.add(current)
                    header = read(current, LIST_HEADER_SIZE)
                    stats = read_stats(read, current + 0x30)
                    if stats != read_stats(read, current + 0x30) or read(current, LIST_HEADER_SIZE) != header:
                        raise ValueError('Candidate modifier list changed')
                    if any(s['id'] >= 2048 for s in stats):
                        raise ValueError('Candidate stat ID outside research bound')
                    chain['lists'].append({'address': current, 'header_hex': header.hex(), 'stats': stats})
                    current = struct.unpack_from('<Q', header, PREVIOUS_LINK_OFFSET)[0]
                chain['complete'] = True
            except (OSError, ValueError, struct.error) as exc:
                chain['reason'] = str(exc)
        result['stable'] = read(pointer, ROOT_HEADER_SIZE) == root
    except (OSError, ValueError, struct.error) as exc:
        result.update(stable=False, reason=str(exc))
    return result
