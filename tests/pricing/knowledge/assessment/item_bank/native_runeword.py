"""Opt-in native ItemData/child evidence for recipe identity and report ranges."""

import struct

from inventory_tracking.items.identity import (
    ETHEREAL_FLAG,
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
    RUNEWORD_FLAG,
    RUNEWORD_OFFSET,
    SOCKETED_FLAG,
    resolve_identity,
)
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from inventory_tracking.items.stat_constants import TOTAL_STATS_DESCRIPTOR_OFFSET
from tests.pricing.knowledge.assessment.item_bank.models import Item


class NativeRunewordItem(Item):
    def capture(self):
        quality = {'low_quality': 1, 'normal': 2, 'superior': 3}.get(self.rarity)
        if quality is None or type(self.ethereal) is not bool:
            raise ValueError('Native runeword fixture needs known quality and ethereal flag')
        result = super().capture()
        base = next(b for b in metadata()['bases'].values() if b['name'] == self.base)
        data = bytearray(ITEM_DATA_SIZE)
        struct.pack_into('<I', data, QUALITY_OFFSET, quality)
        flags = (IDENTIFIED_FLAG if self.identified else 0) | (ETHEREAL_FLAG if self.ethereal else 0)
        flags |= RUNEWORD_FLAG if self.runeword else 0
        flags |= SOCKETED_FLAG if self.sockets else 0
        struct.pack_into('<I', data, FLAGS_OFFSET, flags)
        # Unknown native prefix deliberately forces observed recipe resolution.
        struct.pack_into('<H', data, RUNEWORD_OFFSET, 65535)
        children = [child.native_capture(i) for i, child in enumerate(self.socket_items)]
        for child in children:
            child['unit'].update(type=4, identity_stable=True)
        arrays = {
            'item_data_hex': data.hex(),
            'arrays': [
                {
                    'header_offset': TOTAL_STATS_DESCRIPTOR_OFFSET,
                    'stats': [{'id': sid, 'layer': layer, 'raw': raw} for sid, layer, raw in self.raw_stats],
                }
            ],
            'socket_items': {
                'complete': self.socket_contents == 'filled' and len(self.socket_items) == self.sockets,
                'children': children,
            },
        }
        identity = resolve_identity({'quality': quality}, arrays, base)
        result['item']['name'] = identity['name'] if identity else base['name']
        result['item']['runeword'] = identity['name'] if identity else None
        if identity:
            result['source']['item_identity'] = {
                key: identity[key] for key in ('table', 'table_id', 'offset', 'method', 'observed_table_id')
            }
            annotate_roll_ranges(result['decoded_stats'], identity)
        return result
