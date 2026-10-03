"""Historical collection observations exercise real original ethereal armor totals."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/ethereal_owned_armor.json').read_text())


@pytest.mark.parametrize('record', RECORDS, ids=lambda row: row['name'])
@pytest.mark.parametrize('delta', [0, -1, 1])
def test_owned_ethereal_total_defense(record, delta):
    observation = deepcopy(record['observation'])
    defense = next(row for row in observation['decoded_stats'] if row['memory_stat']['id'] == 31)
    defense['value'] += delta
    defense['memory_stat']['raw'] += delta
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (delta == 0), gaps
    if delta:
        assert any('total defense' in gap for gap in gaps)
