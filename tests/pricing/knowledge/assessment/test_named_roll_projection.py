from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def mara(resistance=30):
    values = {**dict.fromkeys((0, 1, 2, 3), 5), 127: 2, **dict.fromkeys((39, 41, 43, 45), resistance)}
    mapping = {s: metadata()['stats'][str(s)]['property_id'] for s in values}
    return replace(
        facts('Amulet', 'unique', "Mara's Kaleidoscope"),
        stats={f'{s}:0': {'status': 'decoded', 'value': v, 'market_property': mapping[s]} for s, v in values.items()},
        properties={mapping[s]: v for s, v in values.items()},
    )


@pytest.mark.parametrize('mode', ['missing', 'changed', 'missing_mapping'])
def test_named_variable_roll_cannot_disappear_from_contract(mode):
    item = mara()
    prop = item.stats['39:0']['market_property']
    properties = dict(item.properties)
    if mode == 'changed':
        properties[prop] = 20
    else:
        properties.pop(prop)
    stats = dict(item.stats)
    if mode == 'missing_mapping':
        stats['39:0'] = {k: v for k, v in stats['39:0'].items() if k != 'market_property'}
    contract, gaps = NamedHandler().contract(replace(item, properties=properties, stats=stats), 'jewelry')
    assert contract is None
    assert any('39:0' in gap and 'projection' in gap for gap in gaps)


def test_complete_named_rolls_remain_distinct():
    contracts = [NamedHandler().contract(mara(value), 'jewelry')[0] for value in (20, 30)]
    assert all(contracts)
    assert contracts[0].properties != contracts[1].properties
