"""Fixed compound cold duration and rolled duration retain different semantics."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_cold_duration.json').read_text())['records']


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value', 'unit', 'unknown'])
def test_named_cold_duration_is_required_and_only_fixed_value_is_intrinsic(record, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(r for r in rows if r.get('memory_stat', {}).get('id') == 56)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 0.04
    elif mutation == 'unit':
        row['unit'] = 'frames'
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (record['name'] == 'Hellrack' and mutation == 'unchanged'), gaps
    if contract is None:
        assert gaps


@pytest.mark.parametrize('stat', [48, 49, 50, 51, 54, 55])
@pytest.mark.parametrize('mutation', ['missing', 'raw', 'value'])
def test_hellrack_fixed_elemental_endpoints_require_raw_and_decoded_agreement(stat, mutation):
    record = next(r for r in RECORDS if r['name'] == 'Hellrack')
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(r for r in rows if r.get('memory_stat', {}).get('id') == stat)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    else:
        row['value'] += 1
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is None, gaps
