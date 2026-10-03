"""Omitting a variable-level proc must not manufacture a priceable item."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_variable_triggers.json').read_text())['records']


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('missing', [False, True])
def test_variable_proc_cannot_disappear_from_named_comparison(record, missing):
    observation = deepcopy(record['observation'])
    key = record['gaps'][0].split('stat ')[1][:-1]
    stat, layer = map(int, key.split(':'))
    if missing:
        observation['decoded_stats'] = [
            row
            for row in observation['decoded_stats']
            if (row.get('memory_stat', {}).get('id'), row.get('memory_stat', {}).get('layer')) != (stat, layer)
        ]
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    if record['name'] == 'Stormspire' and not missing:
        assert contract is not None, gaps
        assert contract.trigger_levels == {'433': 20}
    else:
        assert contract is None, 'A missing variable proc cannot become a fixed-identity invariant'
        assert gaps
