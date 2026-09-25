from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.market_projection import market_properties
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.handlers.random_skills import comparison_gaps
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def torch():
    return facts('Large Charm', 'unique', 'Hellfire Torch')


@pytest.mark.parametrize('class_id', range(8))
def test_torch_requires_one_random_class_bonus_and_its_market_projection(class_id):
    definition = named_definitions()['unique', 'Hellfire Torch']
    key = f'83:{class_id}'
    item = replace(torch(), stats={key: {'status': 'decoded', 'value': 3}})
    assert comparison_gaps(item, definition)
    assert not comparison_gaps(item, definition, require_projection=False)
    item = replace(item, properties={market_properties()[key]: 3})
    assert not comparison_gaps(item, definition)
    assert comparison_gaps(replace(item, stats={}), definition, require_projection=False)
    multiple = replace(item, stats={**item.stats, f'83:{(class_id + 1) % 8}': {'status': 'decoded', 'value': 3}})
    assert comparison_gaps(multiple, definition, require_projection=False)
    assert comparison_gaps(replace(item, capture_complete=False), definition, require_projection=False)


@pytest.mark.parametrize(
    ('layer', 'value', 'status'), [(8, 3, 'decoded'), (0, 2, 'decoded'), (0, 4, 'decoded'), (0, 3, 'unresolved')]
)
def test_invalid_torch_class_payload_is_rejected(layer, value, status):
    definition = named_definitions()['unique', 'Hellfire Torch']
    item = replace(torch(), stats={f'83:{layer}': {'status': status, 'value': value}})
    assert comparison_gaps(item, definition, require_projection=False)
