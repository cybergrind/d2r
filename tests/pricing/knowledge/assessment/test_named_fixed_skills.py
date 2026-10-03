"""Fixed named skills keep their exact native layer and bonus, including +4/+5."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_fixed_skills.json').read_text())['records']
FIXED = [r for r in RECORDS if r['name'] not in ('Bloodletter', 'Frostwind')]
VARIABLE = [r for r in RECORDS if r['name'] in ('Bloodletter', 'Frostwind')]


@pytest.mark.parametrize('record', FIXED, ids=lambda r: r['name'])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value', 'layer', 'unknown'])
def test_fixed_named_skill_requires_exact_native_skill_and_bonus(record, mutation):
    observation = deepcopy(record['observation'])
    key = record['gaps'][0].removeprefix('No verified market mapping for native stat ').removesuffix('.')
    stat, layer = map(int, key.split(':'))
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == stat and s['memory_stat']['layer'] == layer)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 1
    elif mutation == 'layer':
        row['memory_stat']['layer'] += 1
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (mutation == 'unchanged'), gaps
    if mutation != 'unchanged':
        assert gaps


@pytest.mark.parametrize('record', VARIABLE, ids=lambda r: r['name'])
def test_unmapped_variable_named_skills_remain_comparison_gaps(record):
    facts = normalize(record['observation'])
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is None
    assert set(record['gaps']) <= set(gaps)
