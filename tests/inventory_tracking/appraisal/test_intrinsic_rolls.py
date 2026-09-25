from copy import deepcopy

import pytest

from inventory_tracking.items.metadata import decode_stats
from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.policies.test_socketed_ravenlore import raven


def record(total, contribution):
    item = raven(total, contribution)
    rows, _, _ = decode_stats([{'id': 333, 'layer': 0, 'raw': total}])
    annotate_roll_ranges(rows, thaw(catalog().named['unique', 'Ravenlore']))
    return {
        'extraction': {'item': item.to_dict(), 'decoded_stats': rows},
        'assessment': {'trade_tier': assess_tier(item)},
    }


@pytest.mark.parametrize(
    ('total', 'socket', 'intrinsic', 'quality'), [(25, 5, 20, 'perfect'), (20, 5, 15, 'normal'), (15, 5, 10, 'low')]
)
def test_display_keeps_total_but_ranks_intrinsic_roll(total, socket, intrinsic, quality):
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats

    result = record(total, socket)
    original = deepcopy(result)
    row = display_stats(result)[0]
    assert row['value'] == total
    assert row['roll_quality'] == quality
    assert row['text'] == f'-{total}% to Enemy Fire Resistance — item roll: {intrinsic} (10-20), sockets: +{socket}'
    assert result == original


def test_unverified_socket_total_cannot_keep_a_perfect_color_or_range():
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats

    result = record(20, 5)
    result['assessment']['trade_tier'] = {'status': 'pending_review'}
    row = display_stats(result)[0]
    assert row['text'] == '-20% to Enemy Fire Resistance — item range: 10-20'
    assert 'roll_quality' not in row
    assert 'roll_range' not in row


def test_shared_presentation_and_tone_lookup_use_intrinsic_quality():
    from inventory_tracking.appraisal.presentation import ItemAssessment, result_tones
    from inventory_tracking.presentation import Tone

    result = record(25, 5)
    result['decision'] = {}
    expected = '-25% to Enemy Fire Resistance — item roll: 20 (10-20), sockets: +5'
    assert result_tones(result)[expected] == Tone.PERFECT
    document = ItemAssessment.from_record({'request_id': 'intrinsic-test', 'state': 'complete', 'result': result})
    assert any(line.text.strip() == expected and line.tone == Tone.PERFECT for line in document.lines)
    assert not result_tones(record(20, 5))


def test_mismatched_intrinsic_evidence_cannot_color_a_different_capture():
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats

    result = record(20, 5)
    result['assessment']['trade_tier']['intrinsic_rolls']['333:0']['observed'] = 25
    assert 'roll_quality' not in display_stats(result)[0]


def test_saved_shako_keeps_its_independently_verified_base_defense_range():
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats
    from pricing.knowledge.assessment.maintenance.replay import replay

    result = replay('harlequin_crest')
    row = next(r for r in display_stats(result) if r.get('memory_stat', {}).get('id') == 31)
    assert row['text'] == 'Defense: 99 (98-141)'
    assert row['roll_quality'] == 'low'


@pytest.mark.parametrize('contents', [None, 'unknown', 'empty'])
def test_unknown_or_conflicting_occupancy_cannot_publish_intrinsic_range(contents):
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats

    result = record(20, 5)
    item = result['extraction']['item']
    item.update(socket_contents=contents, filled_sockets=None, empty_sockets=None)
    if contents != 'empty':
        item['socket_items'] = []
    # Keep previous tier proof to verify that uncertain current occupancy cannot
    # accidentally reuse it; the captured total alone looks like a perfect roll.
    original = deepcopy(result)
    row = display_stats(result)[0]
    assert row['text'] == '-20% to Enemy Fire Resistance — item range: 10-20'
    assert 'roll_quality' not in row
    assert 'roll_range' not in row
    assert result == original


@pytest.mark.parametrize('sockets', [0, 1])
def test_verified_empty_item_keeps_its_native_range(sockets):
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats

    result = record(20, 5)
    result['assessment']['trade_tier'] = {'status': 'pending_review'}
    result['extraction']['item'].update(
        sockets=sockets, socket_contents='empty', socket_items=[], filled_sockets=0, empty_sockets=sockets
    )
    row = display_stats(result)[0]
    assert row['roll_quality'] == 'perfect'
    assert row['roll_range']['max'] == 20


def test_guardian_angel_keeps_definition_bounds_without_asserting_unknown_socket_roll():
    from inventory_tracking.appraisal.intrinsic_rolls import display_stats
    from pricing.knowledge.assessment.maintenance.replay import replay

    result = replay('guardian_angel')
    row = next(r for r in display_stats(result) if r.get('memory_stat', {}).get('id') == 16)
    assert row['text'] == '+187% Enhanced Defense — item range: 180-200'
    assert 'roll_quality' not in row
    assert 'roll_range' not in row
