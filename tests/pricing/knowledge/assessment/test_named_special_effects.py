"""Keep verified effect semantics without treating cosmetic intensity as value."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_special_effects.json').read_text())['records']
MAPPED = [r for r in RECORDS if r['name'] == 'Hellcast']
RECORDS = [r for r in RECORDS if r['name'] != 'Hellcast']
STATS = {'Gorefoot': 140, 'Tomb Reaver': 155, "M'avina's Caster": 157}


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value', 'layer', 'unknown'])
def test_special_named_effects_require_native_values(record, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == STATS[record['name']])
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


@pytest.mark.parametrize('intensity', [2, 3, 4, 5, 6])
def test_gorefoot_cosmetic_intensity_requires_native_bounds_but_does_not_change_contract(intensity):
    observation = deepcopy(next(r['observation'] for r in RECORDS if r['name'] == 'Gorefoot'))
    row = next(s for s in observation['decoded_stats'] if s.get('memory_stat', {}).get('id') == 140)
    row['value'] = row['memory_stat']['raw'] = intensity
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (3 <= intensity <= 5), gaps
    if contract:
        original = normalize(next(r['observation'] for r in RECORDS if r['name'] == 'Gorefoot'))
        reference, reference_gaps = NamedHandler().contract(original, classify(original)[0])
        assert not reference_gaps
        assert contract == reference


@pytest.mark.parametrize('record', MAPPED, ids=lambda r: r['fingerprint'][:8])
def test_existing_mapped_arrow_effect_is_preserved(record):
    facts = normalize(record['observation'])
    assert facts.stats['158:0']['market_property'] is not None
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert contract is not None, gaps
