from copy import deepcopy

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment, result_tones
from inventory_tracking.presentation import Tone
from tests.inventory_tracking.appraisal.test_text import saved_result


USE = {
    'runeword': 'Infinity',
    'role': 'Act 2 mercenary',
    'status': 'perfect preferred base',
    'strengths': ['Ethereal preferred base'],
    'missing': [],
    'tradeoff': 'Check mercenary requirements',
    'alternatives': [],
}
LABEL = 'Infinity / Act 2 mercenary: perfect preferred base'


@pytest.mark.parametrize('legacy', [None, {'uses': [{**USE, 'runeword': 'Outdated recipe'}]}])
def test_current_base_result_drives_text_and_colors_without_legacy_mirror(legacy):
    record = saved_result()
    result = record['result']
    result['assessment'] = {'base_uses': [deepcopy(USE)]}
    if legacy is not None:
        result['base_assessment'] = legacy
    else:
        result.pop('base_assessment', None)
    before = deepcopy(record)
    doc = ItemAssessment.from_record(record)
    assert LABEL in doc.to_text()
    assert 'Outdated recipe' not in doc.to_text()
    assert next(line for line in doc.to_osd() if line.text.strip() == LABEL).tone == Tone.PREFERRED
    assert result_tones(result)[LABEL] == Tone.PREFERRED
    assert doc.to_rich().plain == doc.to_text()
    assert record == before


def test_empty_current_result_rejects_stale_fit_but_retains_generic_recipe_evidence():
    record = saved_result()
    record['result']['assessment'] = {'base_uses': []}
    record['result']['base_assessment'] = {'uses': [deepcopy(USE)], 'recipes': [{'runeword': 'Infinity'}]}
    text = ItemAssessment.from_record(record).to_text()
    assert LABEL not in text
    assert 'Runeword options (check recipe conditions): Infinity' in text
    assert LABEL not in result_tones(record['result'])


def test_archival_report_without_current_base_field_still_renders():
    record = saved_result()
    record['result'].pop('assessment', None)
    record['result']['base_assessment'] = {'uses': [deepcopy(USE)]}
    assert LABEL in ItemAssessment.from_record(record).to_text()
