from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('quality', ['superior', 'magic', 'rare'])
def test_base_tier_listing_metadata_must_match_verified_base(quality):
    item = replace(
        facts('Cinquedeas', quality),
        stats={f'{stat}:0': {'status': 'decoded', 'value': 15} for stat in (17, 18)},
        properties={'510': 15},
    )
    contract, gaps = HANDLERS['base' if quality == 'superior' else 'affixed'].contract(item, 'weapon')
    assert not gaps
    contract = contract.to_dict()
    assert contract.get('base_tier') == 'Exceptional'
    row = {
        'name': item.base_name,
        'base_code': item.base_code,
        'rarity': quality,
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
        'properties': {'510': 15, '930': 'Exceptional'},
    }
    assert not reject_reasons(contract, row)
    for tier in ('Normal', 'Elite', None, ['Exceptional']):
        assert reject_reasons(contract, {**row, 'properties': {'510': 15, '930': tier}})
    assert not reject_reasons(contract, {**row, 'properties': {'510': 15}})
    assert reject_reasons({**contract, 'base_tier': None}, row)
