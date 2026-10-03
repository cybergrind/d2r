"""Fixed repair rates are native identity effects, not variable market fields."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_self_repair.json').read_text())['records']


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'seconds', 'rate', 'unknown'])
def test_named_repair_requires_exact_rate_and_display_seconds(record, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == 252)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'seconds':
        row['value'] += 1
    elif mutation == 'rate':
        row['memory_stat']['raw'] -= 1
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (mutation == 'unchanged'), gaps
    if mutation != 'unchanged':
        assert gaps
