import json
from pathlib import Path

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.metadata import decode_stats, item_base
from inventory_tracking.items.ranges import annotate_roll_ranges


def test_captured_rare_ring_uses_rare_eligible_tiers():
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/rare_ring_affixes.json').read_text())
    base = item_base(capture['txt_id'])
    context = resolve_affix_ranges(capture['details'], capture['arrays'], base)
    decoded, _, _ = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=base)
    annotate_roll_ranges(decoded, context)
    texts = [r['text'] for r in decoded]
    assert '+5 (1-90) to Mana [T6; T1: 61-90]' in texts
    assert 'Fire Resist +28% (5-50%) [T2; T1: 31-50%]' in texts
    assert not any('/' in s.split('[T')[-1] for s in texts if '[T' in s)


def test_magic_ring_can_use_magic_only_top_mana_tier():
    import struct

    capture = json.loads((Path(__file__).parents[1] / 'fixtures/rare_ring_affixes.json').read_text())
    raw = bytearray.fromhex(capture['arrays']['item_data_hex'])
    struct.pack_into('<I', raw, 0, 4)
    struct.pack_into('<6H', raw, 0x48, 1090, 0, 0, 174, 0, 0)
    capture['arrays']['item_data_hex'] = raw.hex()
    capture['details']['quality'] = 4
    context = resolve_affix_ranges(capture['details'], capture['arrays'], item_base(capture['txt_id']))
    assert context is not None
    assert context['roll_ranges']['9']['quality_range']['max'] == 120
    assert context['roll_ranges']['9']['tiers'][0] == {'min': 91, 'max': 120}
