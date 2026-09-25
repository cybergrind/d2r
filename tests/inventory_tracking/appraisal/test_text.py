import copy
import json
from pathlib import Path

from inventory_tracking.appraisal.text import format_appraisal, unresolved_lines


def saved_result():
    return json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_result.json').read_text())


def test_saved_host_draft_is_readable_and_preserves_uncertainty():
    text = format_appraisal(saved_result())
    assert 'Magic Ring' in text
    assert '\n  +10% Faster Cast Rate\n' in text
    assert '+11 Maximum Stamina' in text
    assert 'Price: unresolved' in text
    assert 'Verdict:' not in text
    assert 'Title, required level' not in text
    assert 'No priced, verified single-unit comparisons' not in text
    assert 'property_id' not in text
    assert '\\n' not in text


def test_unknown_stats_and_dated_asks_are_not_a_valuation():
    record = copy.deepcopy(saved_result())
    record['result']['extraction']['unresolved_stats'] = [{'id': 999, 'raw': 12, 'layer': 0}]
    record['result']['evidence']['identity']['market']['representatives'] = [
        {'ask_ist': 2, 'observed_at': '2026-09-18', 'source': 'local cached asks'},
        {'ask_ist': 99, 'observed_at': None},
    ]
    text = format_appraisal(record)
    assert '1 stat entry remains undecoded' in text
    assert '2026-09-18 ask: 2 Ist' not in text
    assert '99 Ist' not in text
    assert 'Price: unresolved' in text


def test_rejection_is_plain_text():
    text = format_appraisal({'request_id': 2, 'state': 'rejected', 'reason': 'Unsupported inventory widget'})
    assert '\nUnavailable: Unsupported inventory widget\n' in text
    assert 'Price:' not in text


def test_host_large_charm_with_null_market_still_displays_stats():
    record = json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_charm_result.json').read_text())
    assert record['result']['evidence']['identity']['market'] is None
    text = format_appraisal(record)
    assert 'Magic Large Charm' in text
    assert '\n  +35 to Life\n  +4 to Mana\n' in text
    assert 'Price: unresolved' in text


def test_highlights_include_undecoded_properties_and_stats_only():
    record = saved_result()
    extraction = record['result']['extraction']
    extraction['decoded_stats'] = [
        {'status': 'decoded', 'text': '+39% Poison Resist'},
        {'status': 'unresolved', 'text': 'Self-repair: raw 3 (interpretation unresolved)'},
    ]
    marked = unresolved_lines(record)
    assert extraction['review'][0] not in marked
    assert extraction['decoded_stats'][1]['text'] in marked
    assert extraction['decoded_stats'][0]['text'] not in marked


def test_unpriced_report_states_actual_blocker_without_market_boilerplate():
    from inventory_tracking.appraisal.text import price_lines

    result = {
        'price_estimate': {
            'estimate_ist': None,
            'unavailable_reason': 'unclassified',
            'notes': ['Asks are not confirmed sale prices.', 'Need 3 independent comparable sellers; found 0.'],
        },
        'assessment': {
            'quality_policy': 'named',
            'price_gaps': ['Total defense is required for this armor comparison.'],
        },
    }
    assert price_lines(result) == ['Price: not assessed — Total defense is required for this armor comparison.']
    result['price_estimate']['unavailable_reason'] = 'no_matches'
    assert price_lines(result) == ["Price: unknown — no offline listings match this item's variant."]


def test_normal_report_omits_diagnostics_and_empty_sections_but_keeps_item_issues():
    record = saved_result()
    result = record['result']
    result['extraction']['issues'] = ['Enhanced damage percentage was not captured.']
    result['base_assessment'] = {
        'historical_asks': [{'details': {'median_ist': 99}}],
        'research': [{'date': '2026-09-18', 'details': {'demand': {}}}],
        'recipes': [],
        'price_status': 'historical_asks_only',
    }
    result['assessment'] = {
        'family': 'weapon',
        'quality_policy': 'base',
        'roles': [],
        'coverage_gaps': ['No reviewed build-role profile applies.'],
    }
    result['decision']['reason'] = 'Memory snapshot with limited stat decoding; local evidence requires review.'
    text = format_appraisal(record)
    assert 'Enhanced damage percentage was not captured.' in text
    for noise in [
        'Coverage:',
        'Assessment:',
        'Historical buckets',
        'Research (',
        'see JSON',
        'Memory snapshot',
        'Snapshot evidence',
        'Verdict:',
        'Next:',
        'Offline evidence',
        'Title, required level',
        'Unresolved / review:',
    ]:
        assert noise not in text
    result['extraction']['issues'] = []
    assert 'Unreadable:' not in format_appraisal(record)
    assert result['extraction']['review']  # Diagnostics remain available in JSON.


def test_report_does_not_anchor_item_to_unrelated_same_base_price():
    from inventory_tracking.appraisal.text import price_lines

    lines = price_lines(
        {
            'price_estimate': {'estimate_ist': None, 'notes': []},
            'price_reference': {'median_ist': 97.0785, 'priced_sellers': 4},
        }
    )
    assert '97.0785' not in '\n'.join(lines)
    assert any('not comparable' in line for line in lines)
