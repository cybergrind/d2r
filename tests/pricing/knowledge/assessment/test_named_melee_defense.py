"""Real named captures retain exact fixed melee defense without a market field."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_melee_defense.json').read_text())['records']


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'value', 'raw', 'fractional', 'unknown'])
def test_fixed_melee_defense_requires_exact_native_capture(record, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == 33)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'value':
        row['value'] += 1
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'fractional':
        row['value'] += 0.5
    elif mutation == 'unknown':
        row['status'] = 'unresolved'
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (mutation == 'unchanged'), gaps
    if mutation != 'unchanged':
        assert gaps


@pytest.mark.parametrize('mutation', ['variable', 'wrong_property', 'wrong_layer', 'native_mismatch'])
def test_fixed_melee_defense_requires_native_definition_agreement(mutation):
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
    from pricing.knowledge.assessment.mechanics.named_fixed_stats import fixed_scalar_keys

    facts = normalize(RECORDS[0]['observation'])
    definition, gaps = resolve_named_definition(facts)
    assert not gaps
    definition = dict(definition)
    definition['roll_ranges'] = {k: dict(v) for k, v in definition['roll_ranges'].items()}
    definition['game_definition'] = dict(definition['game_definition'])
    spec = next(s for s in definition['roll_ranges'].values() if s['stat_id'] == 33)
    if mutation == 'variable':
        spec['max'] += 1
    elif mutation == 'wrong_property':
        spec['property'] = 'ac'
    elif mutation == 'wrong_layer':
        spec['layer'] = 1
    elif mutation == 'native_mismatch':
        native = definition['game_definition']
        slot = next(i for i in range(1, 13) if native.get(f'prop{i}') == 'ac-hth')
        native[f'min{slot}'] += 1
    consumed, gaps = fixed_scalar_keys(facts, definition)
    assert consumed == set()
    assert gaps
