import json
from pathlib import Path

import pytest

from inventory_tracking.items.defense import defense_range_context
from inventory_tracking.items.identity import resolve_identity
from inventory_tracking.items.metadata import decode_stats, item_base
from inventory_tracking.items.ranges import annotate_roll_ranges


FIXTURE = Path(__file__).parents[1] / 'fixtures/harlequin_crest.json'


def test_captured_shako_defense_is_a_low_base_roll():
    capture = json.loads(FIXTURE.read_text())
    base = item_base(capture['txt_id'])
    identity = resolve_identity(capture['details'], capture['arrays'], base)
    context = defense_range_context(capture['arrays'], identity)
    decoded, _, _ = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=base)
    annotate_roll_ranges(decoded, context)
    defense = next(r for r in decoded if r.get('memory_stat', {}).get('id') == 31)
    assert defense['text'] == 'Defense: 99 (98-141)'
    assert defense['roll_quality'] == 'low'


@pytest.mark.parametrize('change', ['missing_base', 'modified_total', 'ethereal'])
def test_unverified_base_defense_does_not_claim_a_roll(change):
    capture = json.loads(FIXTURE.read_text())
    arrays = capture['arrays']
    identity = resolve_identity(capture['details'], arrays, item_base(capture['txt_id']))
    if change == 'missing_base':
        arrays['arrays'] = arrays['arrays'][1:]
    elif change == 'modified_total':
        next(r for r in arrays['arrays'][-1]['stats'] if r['id'] == 31)['raw'] += 10
    else:
        raw = bytearray.fromhex(arrays['item_data_hex'])
        raw[0x1A] |= 0x40
        arrays['item_data_hex'] = raw.hex()
    assert defense_range_context(arrays, identity) is None
