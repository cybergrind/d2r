from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def armor(index=None, enhancement=None, durability=None):
    stats = {'31:0': {'status': 'decoded', 'value': 250, 'raw': 250}}
    properties = {}
    for stat, prop, value in ((16, '425', enhancement), (75, '937', durability)):
        if value is not None:
            stats[f'{stat}:0'] = {'status': 'decoded', 'raw': value, 'value': value}
            properties[prop] = value
    source = {} if index is None else {'superior_quality': {'table_id': index, 'offset': 0x34, 'category': 'armor'}}
    return replace(facts('Mage Plate', 'superior'), stats=stats, properties=properties, provenance={'capture': source})


def test_superior_armor_missing_enhancement_is_not_a_complete_comparison():
    contract, gaps = HANDLERS['base'].contract(armor(), 'armor')
    assert contract is None
    assert 'Armor enhancement coverage is unproven.' in gaps


def test_verified_durability_only_armor_requires_zero_enhancement_in_listings():
    from pricing.knowledge.assessment.comparables import reject_reasons

    contract, gaps = HANDLERS['base'].contract(armor(4, durability=12), 'armor')
    assert contract is not None, gaps
    assert contract.properties == {'1855': 250, '937': 12, '425': 0}
    payload = contract.to_dict()
    row = {
        **payload,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(payload, row)
    assert reject_reasons(payload, {**row, 'properties': {'1855': 250, '937': 12}})


@pytest.mark.parametrize(('index', 'enhancement', 'durability'), [(2, None, None), (7, 15, None), (7, 16, 12)])
def test_selected_armor_pattern_requires_all_declared_rolls(index, enhancement, durability):
    contract, gaps = HANDLERS['base'].contract(armor(index, enhancement, durability), 'armor')
    assert contract is None
    assert any('Superior quality' in gap for gap in gaps)


def test_complete_superior_armor_pattern_retains_both_modifiers():
    contract, gaps = HANDLERS['base'].contract(armor(7, 15, 12), 'armor')
    assert contract is not None, gaps
    assert contract.properties['425'] == 15
    assert contract.properties['937'] == 12


def test_armor_contract_preserves_base_code_and_rejects_conflicting_listing_identity():
    from pricing.knowledge.assessment.comparables import reject_reasons

    item = armor(7, 15, 12)
    contract, gaps = HANDLERS['base'].contract(item, 'armor')
    assert contract is not None, gaps
    assert contract.base_code == item.base_code
    payload = contract.to_dict()
    row = {
        **payload,
        'base_code': facts('Archon Plate').base_code,
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert reject_reasons(payload, row)
