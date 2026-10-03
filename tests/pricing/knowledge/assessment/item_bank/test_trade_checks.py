from copy import deepcopy

import pytest

from tests.pricing.knowledge.assessment.item_bank.trade_checks import assert_trade_checks


CHECKS = {
    'schema_version': 1,
    'qualification': {'status': 'candidate', 'material_stats': []},
    'lines': [{'text': 'Trade: candidate — Fixed stats.', 'tone': 'tier_high'}],
}
RESULT = {
    'decision': {},
    'extraction': {
        'item': {'name': 'The Stone of Jordan', 'rarity': 'unique'},
        'decoded_stats': [],
        'unresolved_stats': [],
    },
    'assessment': {
        'trade_tier': {'tier': 'high'},
        'trade_qualification': {'status': 'candidate', 'material_stats': [], 'reason': 'Fixed stats.'},
    },
}


def test_trade_receipt_asserts_the_actual_rendered_status_and_color():
    assert_trade_checks(RESULT, CHECKS)


@pytest.mark.parametrize('corruption', ['status', 'material', 'text', 'color'])
def test_trade_receipt_cannot_attest_missing_or_changed_output(corruption):
    result = deepcopy(RESULT)
    if corruption == 'status':
        result['assessment']['trade_qualification']['status'] = 'unresolved'
    elif corruption == 'material':
        result['assessment']['trade_qualification']['material_stats'] = ['60:0']
    elif corruption == 'text':
        result['assessment']['trade_qualification']['reason'] = 'Different claim.'
    else:
        result['assessment']['trade_tier']['tier'] = 'low'
    with pytest.raises(AssertionError):
        assert_trade_checks(result, CHECKS)
