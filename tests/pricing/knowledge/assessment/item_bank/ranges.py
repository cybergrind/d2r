"""Construct explicit named identity evidence; use production range enrichment."""

import struct

from inventory_tracking.items.defense import defense_range_context
from inventory_tracking.items.identity import (
    ETHEREAL_FLAG,
    FLAGS_OFFSET,
    IDENTIFIED_FLAG,
    IDENTITY_OFFSET,
    ITEM_DATA_SIZE,
    QUALITY_OFFSET,
    RUNEWORD_FLAG,
    SOCKETED_FLAG,
    resolve_identity,
)
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.ranges import annotate_roll_ranges


def annotate_named_ranges(item, base, total, decoded):
    quality = {'set': 5, 'unique': 7}.get(item.rarity)
    if quality is None or not item.identified:
        return
    matches = [
        key
        for key, entry in metadata()['identities'][item.rarity].items()
        if entry['name'] == item.name
        and (base['code'] in entry['base_codes'] or base['code'] in entry.get('upgrade_variants', {}))
    ]
    if item.named_table_id is not None:
        matches = [key for key in matches if int(key) == item.named_table_id]
    if len(matches) != 1:
        raise ValueError(f'Named fixture has no unambiguous native identity: {item.name} / {item.base}')
    data = bytearray(ITEM_DATA_SIZE)
    struct.pack_into('<I', data, QUALITY_OFFSET, quality)
    struct.pack_into('<I', data, IDENTITY_OFFSET, int(matches[0]))
    flags = IDENTIFIED_FLAG | (ETHEREAL_FLAG if item.ethereal else 0) | (SOCKETED_FLAG if item.sockets else 0)
    struct.pack_into('<I', data, FLAGS_OFFSET, flags)
    arrays = {
        'item_data_hex': data.hex(),
        # Absence of a discriminator is evidence only for a complete, known
        # unsocketed capture; unknown contents must not become an ordinary item.
        'complete': item.complete and item.sockets == 0 and item.socket_contents == 'empty',
        'arrays': [{'header_offset': 0xE8, 'stats': total}],
    }
    identity = resolve_identity({'quality': quality}, arrays, base)
    annotate_roll_ranges(decoded, identity)
    # Total defense alone cannot prove an unmodified non-ethereal base roll.
    if item.ethereal is False and item.owned_stats is not None:
        arrays['arrays'] = [
            {'header_offset': 0xE8, 'stats': total},
            {
                'header_offset': 0x30,
                'stats': [{'id': stat, 'layer': layer, 'raw': value} for stat, layer, value in item.owned_stats],
            },
        ]
        annotate_roll_ranges(decoded, defense_range_context(arrays, identity))
    return identity


def annotate_affix_ranges(item, base, decoded):
    """Construct native affix bytes from independently authored source-table row IDs."""
    if item.affix_records is None:
        return None
    from inventory_tracking.items.affixes import resolve_affix_ranges

    quality = {'magic': 4, 'rare': 6}[item.rarity]
    data = bytearray(ITEM_DATA_SIZE)
    struct.pack_into('<I', data, QUALITY_OFFSET, quality)
    struct.pack_into('<I', data, FLAGS_OFFSET, IDENTIFIED_FLAG if item.identified else 0)
    for table, offset in (('prefix', 0x48), ('suffix', 0x4E), ('auto', 0x46)):
        records = [record for kind, record in item.affix_records if kind == table]
        if len(records) > (1 if table == 'auto' else 3):
            raise ValueError('Too many test affix records')
        for index, record in enumerate(records):
            matches = [
                int(key)
                for key, entry in metadata()['affixes'][table].items()
                if entry['source']['record_key'] == str(record)
            ]
            if len(matches) != 1:
                raise ValueError('Unknown test affix record')
            struct.pack_into('<H', data, offset + index * 2, matches[0])
    context = resolve_affix_ranges({'quality': quality}, {'item_data_hex': data.hex()}, base)
    annotate_roll_ranges(decoded, context)
    return context.get('native_affixes') if context else None


def annotate_native_staffmods(item, base, decoded):
    """Apply the production post-decode staffmod step with explicit native flags."""
    from inventory_tracking.items.staffmods import annotate_staffmods

    quality = {'low_quality': 1, 'normal': 2, 'superior': 3, 'magic': 4, 'rare': 6, 'crafted': 8}.get(item.rarity)
    if quality is None:
        return
    data = bytearray(ITEM_DATA_SIZE)
    flags = (IDENTIFIED_FLAG if item.identified else 0) | (RUNEWORD_FLAG if item.runeword else 0)
    struct.pack_into('<I', data, FLAGS_OFFSET, flags)
    struct.pack_into('<I', data, QUALITY_OFFSET, quality)
    annotate_staffmods(decoded, {'quality': quality}, {'item_data_hex': data.hex()}, base)
