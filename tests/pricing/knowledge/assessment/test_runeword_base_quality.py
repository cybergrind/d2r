from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def spirit(quality='normal'):
    item = replace(
        facts('Monarch', quality),
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in [(105, 35), (9, 112), (147, 8), (31, 148)]},
    )
    contract, gaps = RunewordHandler().contract(item, 'shield')
    assert not gaps
    return contract.to_dict()


def observation(quality):
    raw = {
        'id': 'one',
        'amount': 1,
        'seller_id': 'seller',
        'prices': [{'name': 'Ist Rune', 'quantity': 1}],
        'properties': [
            {'property_id': 1197, 'type': 'string', 'property': 'Base Item (Shield, Sword) 4', 'string': 'Monarch'}
        ],
    }
    if quality is not None:
        raw['properties'].append({'property_id': 1281, 'type': 'string', 'string': quality})
    row = normalize_listing(raw, name='Spirit', category='runewords', source='fixture', currencies={'ist': 1})
    row.update(scope_status='verified', ethereal=False)
    row['properties']['1855'] = 148
    return row


@pytest.mark.parametrize('quality', ['normal', 'superior', 'low quality'])
def test_base_quality_is_distinct_from_completed_runeword_rarity(quality):
    contract = spirit(quality)
    assert contract['base_rarity'] == quality
    good = observation(quality)
    assert good['rarity'] == 'runeword'
    assert good['base_rarity'] == quality
    assert evaluate(contract, [good])['accepted'] == [good]
    for value in {'normal', 'superior', None, 'ArchonPlate', 'rare'} - {quality}:
        assert not evaluate(contract, [observation(value)])['accepted']


def test_unknown_capture_base_quality_blocks_contract_instead_of_becoming_normal():
    item = replace(
        facts('Monarch'),
        rarity=None,
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in [(105, 35), (9, 112), (147, 8), (31, 148)]},
    )
    contract, gaps = RunewordHandler().contract(item, 'shield')
    assert contract is None
    assert 'Runeword base quality is unknown or incompatible.' in gaps
