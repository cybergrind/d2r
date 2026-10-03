from dataclasses import replace
from datetime import date

import pytest

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication import current_generation
from pricing.knowledge.published_runtime import load_runtime, published_snapshot
from tests.pricing.knowledge.assessment.item_bank.cases.natures_peace_alternatives import ring
from tests.pricing.knowledge.assessment.test_named_fixed_flags import ITEM


@pytest.fixture(scope='module')
def runtime():
    return load_runtime(current_generation('pricing/data/generations'))


@pytest.mark.parametrize(
    ('item', 'valid'),
    [
        (ITEM, True),
        (replace(ITEM, ethereal=True), False),
        (replace(ITEM, raw_stats=tuple(s for s in ITEM.raw_stats if s[0] != 108)), False),
        (ring(), True),
        (ring(depleted=True), True),
        (replace(ring(), raw_stats=tuple(s for s in ring().raw_stats if s[0] != 108)), False),
    ],
    ids=[
        'tyrael-valid',
        'tyrael-impossible-eth',
        'tyrael-missing-rip',
        'nature-valid',
        'nature-depleted',
        'nature-missing-rip',
    ],
)
def test_fixed_flags_through_published_report(runtime, item, valid):
    with published_snapshot(runtime):
        result = retrieve_draft(item.capture(), runtime.database, as_of=date(2026, 10, 3))
        report = format_appraisal({'state': 'complete', 'request_id': 'native-flags', 'result': result})
    assert (result['assessment'].get('contract') is not None) is valid, result['assessment']
    assert item.name in report
    assert 'Trade tier:' in report
    if valid:
        assert 'Slain Monsters Rest in Peace' in report
        assert 'No verified market mapping for native stat 108:0' not in report
    else:
        assert result['price_estimate']['estimate_ist'] is None
        assert result['price_estimate']['basis'] == 'unavailable'
