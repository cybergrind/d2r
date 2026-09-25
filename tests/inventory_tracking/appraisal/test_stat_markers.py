from inventory_tracking.appraisal.stat_markers import stat_line
from inventory_tracking.presentation import StyledLine, render_markup, render_rich


def test_useful_marker_and_bad_roll_have_independent_colors_and_roundtrip():
    row = {
        'status': 'decoded',
        'text': '+10 Mana (10-50)',
        'roll_quality': 'low',
        'memory_stat': {'id': 9, 'layer': 0, 'raw': 10},
    }
    line = stat_line(row, {'9:0': {'desirability': 'desirable'}})
    assert 'desirable' in line.text
    assert '+10 Mana' in line.text
    restored = StyledLine.from_payload(line.to_payload())
    assert restored == line
    rich = render_rich([line])
    assert rich.plain == line.text + '\n'
    assert len({str(span.style) for span in rich.spans}) >= 2
    markup = render_markup([line])
    assert 'foreground="#00ff00"' in markup
    assert 'foreground="#ff0000"' in markup


def test_ambiguous_or_unreviewed_lines_keep_original_roll_style():
    row = {
        'status': 'decoded',
        'text': '<combined damage>',
        'roll_quality': 'perfect',
        'memory_stats': [{'id': 21, 'layer': 0}, {'id': 22, 'layer': 0}],
    }
    line = stat_line(row, {'21:0': {'desirability': 'desirable'}})
    assert line.text == '  <combined damage>'
    assert '&lt;combined damage&gt;' in render_markup([line])
    scalar = {**row, 'memory_stats': [], 'memory_stat': {'id': 21, 'layer': 0}}
    assert stat_line(scalar, {}).text == line.text
    assert stat_line(scalar, {'21:0': {'desirability': 'irrelevant'}}).text == line.text


def test_shared_report_preserves_marker_in_terminal_and_osd_and_rejects_mismatched_spans():
    import pytest

    from inventory_tracking.appraisal.presentation import ItemAssessment

    record = {
        'request_id': 'test',
        'state': 'complete',
        'result': {
            'decision': {'price_status': 'unresolved'},
            'extraction': {
                'item': {'name': 'Test', 'rarity': 'magic'},
                'issues': [],
                'decoded_stats': [
                    {
                        'status': 'decoded',
                        'text': '+10 Mana',
                        'roll_quality': 'low',
                        'memory_stat': {'id': 9, 'layer': 0, 'raw': 10},
                    }
                ],
            },
            'assessment': {'stat_evaluation': {'annotations': {'9:0': {'desirability': 'supporting'}}}},
        },
    }
    document = ItemAssessment.from_record(record)
    line = next(line for line in document.lines if '+10 Mana' in line.text)
    assert '[supporting]' in document.to_text()
    assert line in document.to_osd()
    assert StyledLine.from_payload(line.to_payload()).spans == line.spans
    assert '#77aaff' in render_markup([line])
    assert document.to_rich().plain == document.to_text()
    with pytest.raises(ValueError, match='complete literal line'):
        StyledLine.from_payload({'text': 'original', 'spans': [{'text': 'different', 'tone': 'default'}]})


def test_combined_ed_uses_shared_configuration_meaning_and_preserves_roll_colors():
    row = {
        'status': 'decoded',
        'text': '+201% Enhanced Damage (201-300)',
        'roll_quality': 'low',
        'memory_stats': [{'id': 17, 'layer': 0}, {'id': 18, 'layer': 0}],
    }

    def annotation(*uses):
        return {
            'desirability': 'desirable',
            'configuration_ids': [c for c, _ in uses],
            'contributions': [{'configuration_id': c, 'desirability': m} for c, m in uses],
        }

    shared = annotation(('cruel', 'desirable'))
    line = stat_line(row, {'17:0': shared, '18:0': shared})
    assert '[desirable]' in line.text
    assert '#00ff00' in render_markup([line])
    assert '#ff0000' in render_markup([line])
    assert StyledLine.from_payload(line.to_payload()) == line
    # Aggregate desirability must not pool two unrelated roles into one ED verdict.
    cross = {
        '17:0': annotation(('a', 'desirable'), ('shared', 'supporting')),
        '18:0': annotation(('b', 'desirable'), ('shared', 'supporting')),
    }
    assert '[supporting]' in stat_line(row, cross).text
    for annotations in (
        {'17:0': shared},
        {'17:0': shared, '18:0': annotation(('other', 'desirable'))},
        {'17:0': shared, '18:0': annotation(('cruel', 'supporting'))},
        {'17:0': {'desirability': 'desirable'}, '18:0': {'desirability': 'desirable'}},
    ):
        assert stat_line(row, annotations).text == '  ' + row['text']
    assert stat_line({**row, 'status': 'unresolved'}, {'17:0': shared, '18:0': shared}).text == '  ' + row['text']


def test_real_cruel_configuration_marks_decoder_combined_ed_in_terminal_and_osd():
    import json
    from dataclasses import replace

    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.items.metadata import combine_enhanced_damage
    from pricing.knowledge.assessment.build_profiles import ROOT, build
    from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
    from pricing.knowledge.assessment.profiles import assess_role_results
    from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == 'double-throw-starter-cruel-weapon'
    ]
    item = replace(
        facts('Winged Axe', 'magic'), stats={f'{k}:0': {'status': 'decoded', 'value': 201} for k in (17, 18)}
    )
    context = {'player_class': 'Barbarian'}
    result = StatsEvaluator().evaluate(
        item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
    )
    decoded, _ = combine_enhanced_damage(
        [{'status': 'decoded', 'value': 201, 'memory_stat': {'id': k, 'layer': 0, 'raw': 201}} for k in (17, 18)]
    )
    document = ItemAssessment.from_record(
        {
            'state': 'complete',
            'request_id': 'combined-ed',
            'result': {
                'decision': {'price_status': 'unresolved'},
                'extraction': {
                    'item': {'name': 'Winged Axe', 'rarity': 'magic'},
                    'issues': [],
                    'decoded_stats': decoded,
                },
                'assessment': {'stat_evaluation': {'annotations': result.annotations}},
            },
        }
    )
    line = next(line for line in document.lines if 'Enhanced Damage' in line.text)
    assert '[desirable]' in line.text
    assert line in document.to_osd()
    assert document.to_rich().plain == document.to_text()
    assert document.to_text().count('Enhanced Damage') == 1
