from inventory_tracking.appraisal.stat_markers import stat_line
from inventory_tracking.presentation import Tone


COMPARISON = {
    'deciding': {
        '577': {'native_key': '107:111', 'min': 1, 'max': 3, 'observed_min': 2, 'observed_max': 3, 'better': 'higher'}
    }
}


def row(stat_id, layer, value, quality='low'):
    return {
        'text': str(value),
        'value': value,
        'status': 'decoded',
        'roll_quality': quality,
        'memory_stat': {'id': stat_id, 'layer': layer},
    }


def test_unrelated_minimum_roll_is_not_red_with_a_price_model():
    stat = row(17, 0, 50)
    assert stat_line(stat, {}).tone == Tone.LOW
    assert stat_line(stat, {}, comparison=COMPARISON).tone == Tone.DEFAULT


def test_deciding_roll_colors_follow_the_listed_range():
    assert stat_line(row(107, 111, 1), {}, comparison=COMPARISON).tone == Tone.LOW
    high = stat_line(row(107, 111, 3), {}, comparison=COMPARISON)
    assert high.tone == Tone.PERFECT
    assert '[price roll]' in high.text
    assert stat_line(row(107, 111, None), {}, comparison=COMPARISON).tone == Tone.DEFAULT


def test_lower_is_better_and_out_of_native_range_is_not_green():
    comparison = {
        'deciding': {
            'p': {'native_key': '1:0', 'min': 1, 'max': 10, 'observed_min': 2, 'observed_max': 8, 'better': 'lower'}
        }
    }
    assert stat_line(row(1, 0, 2), {}, comparison=comparison).tone == Tone.PERFECT
    assert stat_line(row(1, 0, 10), {}, comparison=comparison).tone == Tone.LOW
    assert stat_line(row(1, 0, 0), {}, comparison=comparison).tone == Tone.DEFAULT


def test_terminal_and_osd_share_model_colors_without_changing_captured_rows():
    from inventory_tracking.appraisal.presentation import ItemAssessment, result_tones

    ed = row(17, 0, 50)
    ed['text'] = '+50% Enhanced Damage'
    skill = row(107, 111, 3)
    skill['text'] = '+3 Vengeance'
    result = {
        'triage': {'verdict': 'check', 'reason': 'thin evidence', 'band': None, 'roll_comparison': COMPARISON},
        'decision': {'price_status': 'unresolved'},
        'extraction': {'item': {'name': 'Example', 'rarity': 'unique'}, 'issues': [], 'decoded_stats': [ed, skill]},
    }
    document = ItemAssessment.from_record({'request_id': 'colors', 'state': 'complete', 'result': result})
    ed_line = next(line for line in document.lines if 'Enhanced Damage' in line.text)
    skill_line = next(line for line in document.lines if 'Vengeance' in line.text)
    assert ed_line.tone == Tone.DEFAULT
    assert skill_line.tone == Tone.PERFECT
    assert skill_line in document.to_osd()
    assert '[price roll]' in document.to_rich().plain
    assert result_tones(result)[ed['text']] == Tone.DEFAULT
    assert ed['roll_quality'] == 'low'
