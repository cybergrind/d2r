"""Named magic damage is two exact endpoints, not an interval for either stat."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_magic_damage.json').read_text())['records']


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('stat', [52, 53])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value', 'unknown'])
def test_named_magic_damage_requires_both_exact_endpoints(record, stat, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == stat)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 1
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (mutation == 'unchanged'), gaps
    if mutation != 'unchanged':
        assert gaps


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
def test_named_magic_damage_cannot_be_omitted_entirely(record):
    observation = deepcopy(record['observation'])
    observation['decoded_stats'] = [
        row for row in observation['decoded_stats'] if row.get('memory_stat', {}).get('id') not in (52, 53)
    ]
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is None
    assert gaps
