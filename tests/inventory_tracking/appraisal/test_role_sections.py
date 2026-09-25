from copy import deepcopy

from inventory_tracking.appraisal.sections import full_assessment_lines as assessment_lines


def role(variant, **changes):
    return {
        'build': 'nova-sorceress-guide',
        'variant': variant,
        'side': 'merc',
        'slot': 'Weapon',
        'role': 'Insight',
        'status': 'partial',
        'missing': ['Check mercenary requirements.'],
        'preferences': [{'label': 'Level 17 Meditation', 'status': 'false'}],
        'alternatives': ['Insight Giant Thresher'],
        **changes,
    }


def test_equivalent_variant_reports_merge_without_mutating_semantic_roles():
    result = {'assessment': {'roles': [role('Standard'), role('Magic Find')]}}
    original = deepcopy(result)
    lines = assessment_lines(result)
    assert sum('Nova Sorceress' in line for line in lines) == 1
    assert any('Standard, Magic Find' in line for line in lines)
    assert sum('Check mercenary requirements.' in line for line in lines) == 1
    assert result == original


def test_common_conditions_and_preferences_render_once_but_variant_differences_stay_scoped():
    rows = [
        role('Starter', alternatives=['Insight Partizan']),
        role('Standard', missing=['Check mercenary requirements.', 'Requires Cure setup.']),
    ]
    text = '\n'.join(assessment_lines({'assessment': {'roles': rows}}))
    assert text.count('Check mercenary requirements.') == 1
    assert text.count('Level 17 Meditation') == 1
    assert text.index('Requires Cure setup.') > text.index('/ Standard /')
    assert 'Insight Partizan' in text
    assert 'Insight Giant Thresher' in text


def test_matched_and_partial_or_different_wearers_do_not_merge():
    rows = [role('Standard'), role('Magic Find', status='matched', missing=[]), role('Prebuff', side='player')]
    lines = assessment_lines({'assessment': {'roles': rows}})
    assert sum('Nova Sorceress' in line for line in lines) == 3
    assert any('matches item requirements' in line for line in lines)
    assert any('/ player: possible fit' in line for line in lines)
