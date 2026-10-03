"""Input recipes and independently authored appraisal expectations."""

import struct
from dataclasses import dataclass, field

from inventory_tracking.items.identity import (
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
)
from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.socket_payload import decode_payload
from inventory_tracking.items.sockets import annotate_sockets
from inventory_tracking.items.stat_constants import TOTAL_STATS_DESCRIPTOR_OFFSET
from tests.pricing.knowledge.assessment.item_bank.ranges import (
    annotate_affix_ranges,
    annotate_named_ranges,
    annotate_native_staffmods,
)


@dataclass(frozen=True)
class SocketItem:
    base: str
    raw_stats: tuple[tuple[int, int, int], ...] = ()
    complete: bool = False
    name: str | None = None
    unique_table_id: int | None = None
    rare: bool = False

    def native_capture(self, position):
        txt, base = next((key, row) for key, row in metadata()['bases'].items() if row['name'] == self.base)
        if self.rare and (base['type'] != 'jewl' or self.name or self.unique_table_id is not None):
            raise ValueError('Rare socket fixture requires an unnamed ordinary jewel')
        quality = 6 if self.rare else 4 if self.raw_stats else 2
        data = bytearray(ITEM_DATA_SIZE)
        if self.unique_table_id is not None and not self.name:
            raise ValueError('Unique socket variant requires a named identity')
        if self.name:
            matches = [
                key
                for key, row in metadata()['identities']['unique'].items()
                if row['name'] == self.name and base['code'] in row['base_codes']
            ]
            if self.unique_table_id is not None:
                matches = [key for key in matches if int(key) == self.unique_table_id]
            if len(matches) != 1:
                raise ValueError('Socket fixture requires an exact native unique identity')
            quality = 7
            struct.pack_into('<I', data, IDENTITY_OFFSET, int(matches[0]))
        struct.pack_into('<I', data, QUALITY_OFFSET, quality)
        struct.pack_into('<I', data, FLAGS_OFFSET, IDENTIFIED_FLAG)
        return {
            'position': position,
            'unit': {'txt_id': int(txt), 'unit_id': 1000 + position, 'details': {'quality': quality}},
            'item_data_hex': data.hex(),
            'stat_arrays': {
                'complete': self.complete,
                'arrays': [
                    {
                        'header_offset': TOTAL_STATS_DESCRIPTOR_OFFSET,
                        'stats': [{'id': stat, 'layer': layer, 'raw': value} for stat, layer, value in self.raw_stats],
                    }
                ],
            },
        }

    def capture(self, position):
        base = next(row for row in metadata()['bases'].values() if row['name'] == self.base)
        child = {
            'stat_arrays': {
                'complete': self.complete,
                'arrays': [
                    {
                        'header_offset': TOTAL_STATS_DESCRIPTOR_OFFSET,
                        'stats': [{'id': stat, 'layer': layer, 'raw': value} for stat, layer, value in self.raw_stats],
                    }
                ],
            }
        }
        return {
            'name': self.name or self.base,
            'base_code': base['code'],
            'unit_id': 1000 + position,
            'position': position,
            **decode_payload(child, base),
        }


@dataclass(frozen=True)
class Item:
    base: str
    rarity: str
    name: str | None = None
    raw_stats: tuple[tuple[int, int, int], ...] = ()
    ethereal: bool | None = False
    sockets: int | None = 0
    socket_contents: str = 'empty'
    identified: bool = True
    runeword: str | None = None
    viewer_level: int = 80
    complete: bool = False
    affix_records: tuple[tuple[str, int], ...] | None = None
    owned_stats: tuple[tuple[int, int, int], ...] | None = None
    socket_items: tuple[SocketItem, ...] = ()
    named_table_id: int | None = None

    def capture(self):
        # Resolve native codes from the pinned decoder metadata, never from memory.
        base = next(row for row in metadata()['bases'].values() if row['name'] == self.base)
        raw = [{'id': stat, 'layer': layer, 'raw': value} for stat, layer, value in self.raw_stats]
        decoded, affixes, unresolved = decode_stats(raw, base=base, viewer_level=self.viewer_level)
        native_affixes = annotate_affix_ranges(self, base, decoded)
        identity = annotate_named_ranges(self, base, raw, decoded)
        annotate_native_staffmods(self, base, decoded)
        result = {
            'item': {
                'name': self.name or self.base,
                'base_name': self.base,
                'base_code': base['code'],
                'rarity': self.rarity,
                'affixes': affixes,
                'identified': self.identified,
                'ethereal': self.ethereal,
                'sockets': self.sockets,
                'socket_contents': self.socket_contents,
                'socket_items': [child.capture(index) for index, child in enumerate(self.socket_items)],
                'runeword': self.runeword,
            },
            'source': {
                'stat_capture_complete': self.complete,
                **({'native_affixes': native_affixes} if native_affixes is not None else {}),
                **(
                    {
                        'item_identity': {
                            key: identity[key]
                            for key in (
                                'table',
                                'table_id',
                                'offset',
                                'method',
                                'observed_table_id',
                                'mode_eligibility',
                            )
                            if key in identity
                        }
                    }
                    if identity
                    else {}
                ),
            },
            'decoded_stats': decoded,
            'unresolved_stats': unresolved,
        }
        annotate_sockets(
            result['item'],
            decoded,
            {
                'socket_items': {
                    'complete': self.socket_contents == 'empty'
                    or (self.socket_contents == 'filled' and len(self.socket_items) == self.sockets),
                    'children': [child.native_capture(index) for index, child in enumerate(self.socket_items)],
                }
            },
            None,
        )
        return result


@dataclass(frozen=True)
class Case:
    id: str
    item: Item
    context: dict
    expected: dict
    covers: tuple[str, ...] = ()
    report_contains: tuple[str, ...] = ()
    scenario: str = 'positive'
    absent_annotations: tuple[str, ...] = ()
    absent_configurations: tuple[str, ...] = ()
    evidence: tuple[str, ...] = field(default_factory=tuple)
    absent_stat_configurations: dict[str, tuple[str, ...]] = field(default_factory=dict)
    report_absent: tuple[str, ...] = ()
    absent_roles: tuple[str, ...] = ()
    detail_contains: tuple[str, ...] = ()

    report_checks: dict | None = None
    trade_checks: dict | None = None
