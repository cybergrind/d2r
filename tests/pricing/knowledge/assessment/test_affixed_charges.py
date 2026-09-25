from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def orb(remaining=47, maximum=56, level=7, rarity='rare'):
    key = f'204:{48 * 64 + level}'
    return replace(
        facts('Clasped Orb', rarity),
        stats={
            **{f'{stat}:0': {'status': 'decoded', 'raw': 0, 'value': 0} for stat in (17, 18)},
            key: {
                'id': 204,
                'parameter': 48 * 64 + level,
                'status': 'decoded',
                'unit': 'charges_remaining',
                'raw': maximum * 256 + remaining,
                'value': remaining,
                'charges': {'remaining': remaining, 'maximum': maximum},
            },
        },
        properties={'510': 0},
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )


@pytest.mark.parametrize('rarity', ['magic', 'rare'])
def test_rechargeable_affix_matches_skill_level_not_remaining_uses(rarity):
    contract, gaps = HANDLERS['affixed'].contract(orb(rarity=rarity), 'weapon')
    assert contract is not None, gaps
    assert contract.properties['450'] == 7
    assert '450' not in contract.intrinsic_properties
    depleted, gaps = HANDLERS['affixed'].contract(orb(remaining=0, rarity=rarity), 'weapon')
    assert depleted is not None, gaps
    assert depleted.properties == contract.properties
    payload = contract.to_dict()
    rows = [
        {
            **payload,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 1,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0}})
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0, '450': 47}})


@pytest.mark.parametrize(
    'item',
    [orb(maximum=55), orb(level=40), replace(orb(), ethereal=True), replace(orb(), properties={'510': 0, '450': 47})],
)
def test_invalid_or_irreversible_charge_state_cannot_be_compared(item):
    assert HANDLERS['affixed'].contract(item, 'weapon')[0] is None


def test_multiple_eligible_capacities_cannot_share_one_scalar_listing_field(monkeypatch):
    import copy

    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_charges

    data = copy.deepcopy(metadata())
    entry = next(
        v for v in data['affixes']['suffix'].values() if v['name'] == 'of Novas' and orb().base_code in v['base_codes']
    )
    alternate = copy.deepcopy(entry)
    alternate['game_definition']['mod1min'] = 20
    data['affixes']['suffix']['test-alternative'] = alternate
    monkeypatch.setattr(affixed_charges, 'metadata', lambda: data)
    monkeypatch.setattr(affixed_charges, 'metadata_generation', lambda: 'ambiguous-capacity-test')
    contract, gaps = HANDLERS['affixed'].contract(orb(), 'weapon')
    assert contract is None
    assert any('unambiguous' in gap for gap in gaps)


def test_saved_dire_song_charge_mapping_no_longer_blocks_comparison():
    import json
    from pathlib import Path

    from inventory_tracking.items.decode import decode_items
    from pricing.knowledge.assessment.engine import assess_result

    saved = json.loads((Path(__file__).parents[4] / 'tests/inventory_tracking/fixtures/dire_song.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    extraction = decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]
    result = assess_result(extraction, profiles=[])
    assert 'No verified market mapping for native stat 204:3079.' not in result.price_gaps
    assert all('Charged skill' not in gap for gap in result.price_gaps)
    assert result.facts.stats['204:3079']['value'] == 47


def test_charged_skill_can_be_the_only_magic_amulet_affix():
    item = facts('Amulet', 'magic')
    key = f'204:{54 * 64 + 1}'
    item = replace(
        item,
        properties={},
        stats={
            key: {
                'id': 204,
                'parameter': 54 * 64 + 1,
                'status': 'decoded',
                'unit': 'charges_remaining',
                'raw': 22 * 256 + 10,
                'value': 10,
                'charges': {'remaining': 10, 'maximum': 22},
            }
        },
        projection_gaps=[f'No verified market mapping for native stat {key}.'],
    )
    contract, gaps = HANDLERS['affixed'].contract(item, 'jewelry')
    assert contract is not None, gaps
    assert contract.properties == {'526': 1}


def crafted_teleport_amulet(remaining=10):
    parameter = 54 * 64 + 1
    return replace(
        facts('Amulet', 'crafted'),
        properties={'520': 10, '569': 10, '400': 20},
        stats={
            f'204:{parameter}': {
                'id': 204,
                'parameter': parameter,
                'status': 'decoded',
                'unit': 'charges_remaining',
                'raw': 22 * 256 + remaining,
                'value': remaining,
                'charges': {'remaining': remaining, 'maximum': 22},
            }
        },
        projection_gaps=[f'No verified market mapping for native stat 204:{parameter}.'],
    )


def test_crafted_rechargeable_affix_compares_exact_level_and_keeps_recipe_bonuses():
    contract, gaps = HANDLERS['affixed'].contract(crafted_teleport_amulet(), 'jewelry')
    assert contract is not None, gaps
    assert contract.rarity == 'crafted'
    assert contract.properties == {'520': 10, '569': 10, '400': 20, '526': 1}
    empty, gaps = HANDLERS['affixed'].contract(crafted_teleport_amulet(0), 'jewelry')
    assert empty is not None, gaps
    assert empty.properties == contract.properties
    payload = contract.to_dict()
    rows = [
        {
            **payload,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 1,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    assert reject_reasons(payload, {**rows[0], 'rarity': 'rare'})
    assert reject_reasons(payload, {**rows[0], 'properties': {**contract.properties, '526': 2}})


def test_crafted_charge_projection_excludes_magic_only_affixes(monkeypatch):
    import copy

    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics import affixed_charges

    data = copy.deepcopy(metadata())
    for entry in data['affixes']['suffix'].values():
        record = entry['game_definition']
        if record.get('mod1code') == 'charged' and record.get('mod1param') == 54:
            entry['rare'] = False
    monkeypatch.setattr(affixed_charges, 'metadata', lambda: data)
    monkeypatch.setattr(affixed_charges, 'metadata_generation', lambda: 'crafted-magic-only-charges')
    item = crafted_teleport_amulet()
    assert HANDLERS['affixed'].contract(item, 'jewelry')[0] is None
    assert HANDLERS['affixed'].contract(replace(item, rarity='magic'), 'jewelry')[0] is not None
