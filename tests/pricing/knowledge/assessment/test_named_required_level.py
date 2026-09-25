from copy import deepcopy
from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.mechanics.named_requirements import required_level
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.test_comparables import listing
from tests.pricing.knowledge.assessment.test_named_charm_rolls import charm


def gheed():
    item = charm("Gheed's Fortune", 'Grand Charm')
    contract, gaps = NamedHandler().contract(item, 'charm')
    assert not gaps
    row = listing(
        name=item.name,
        rarity='unique',
        base_code=item.base_code,
        sockets=0,
        properties={**dict(contract.properties), '796': 62},
    )
    return contract.to_dict(), row


def test_definition_required_level_allows_exact_named_listing():
    contract, row = gheed()
    before = deepcopy(row)
    result = evaluate(contract, [row])
    assert result['accepted'] == [row], result['rejected']
    assert row == before
    row['properties'].pop('796')
    assert evaluate(contract, [row])['accepted'] == [row]


@pytest.mark.parametrize('level', [61, 63, True, '62', 62.5])
def test_wrong_or_invalid_listing_required_level_is_not_ignored(level):
    contract, row = gheed()
    row['properties']['796'] = level
    assert not evaluate(contract, [row])['accepted']


def test_unverified_required_level_is_not_an_envelope_property():
    contract, row = gheed()
    contract['required_level'] = None
    assert not evaluate(contract, [row])['accepted']


@pytest.mark.parametrize(
    'change',
    [
        {'socket_contents': 'filled'},
        {'socket_contents': None},
        {'capture_complete': False},
        {'base_code': None},
        {'stats': {'92:0': {'status': 'decoded', 'value': 5}}},
        {'stats': {'94:0': {'status': 'decoded', 'value': 10}}},
    ],
)
def test_unverified_requirement_contributions_have_no_proof(change):
    item = replace(charm("Gheed's Fortune", 'Grand Charm'), **change)
    assert required_level(item, catalog().named['unique', item.name]) is None


def test_skill_requirements_and_class_dependent_oskills_are_preserved():
    item = charm("Gheed's Fortune", 'Grand Charm')
    definition = dict(catalog().named['unique', item.name])
    skill = next(k for k, s in metadata()['skills'].items() if s.get('required_level') == 30)
    definition['game_definition'] = {'lvl req': 20}
    single = replace(item, stats={f'107:{skill}': {'status': 'decoded', 'value': 1}})
    assert required_level(single, definition) == 30
    oskill = replace(item, stats={f'97:{skill}': {'status': 'decoded', 'value': 1}})
    assert required_level(oskill, definition) is None
    definition['game_definition'] = {'lvl req': 40}
    assert required_level(oskill, definition) == 40
    unknown = replace(item, stats={'107:999999': {'status': 'decoded', 'value': 1}})
    assert required_level(unknown, definition) is None
