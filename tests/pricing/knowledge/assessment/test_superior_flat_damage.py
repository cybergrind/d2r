from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def weapon(name='Short Sword', low=2, high=8, index=1):
    minimum = 23 if name == 'Short Bow' else 21
    return replace(
        facts(name, 'superior'),
        stats={
            f'{stat}:0': {'status': 'decoded', 'raw': value, 'value': value}
            for stat, value in ((minimum, low), (minimum + 1, high))
        },
        properties={},
        provenance={
            'capture': {
                'superior_quality': {'table_id': index, 'offset': 0x34, 'category': 'weapons'},
                'superior_flat_damage': [{'id': minimum + 1, 'layer': 0, 'raw': 1}],
            }
        },
    )


@pytest.mark.parametrize(('name', 'low', 'high'), [('Short Sword', 2, 8), ('Dagger', 1, 5), ('Short Bow', 1, 5)])
def test_selected_superior_damage_can_be_flat_when_percentage_rounds_to_zero(name, low, high):
    contract, gaps = HANDLERS['base'].contract(weapon(name, low, high), 'weapon')
    assert contract is not None, gaps
    assert contract.properties == {'510': 0, '448': 1}
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
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 5, '448': 1}})


@pytest.mark.parametrize(
    'item',
    [
        weapon(high=9),
        weapon(low=3),
        weapon(index=0),
        weapon('Phase Blade', 31, 36),
        replace(weapon(), ethereal=True),
        replace(weapon(), socket_contents='filled'),
        replace(weapon(), capture_complete=False),
    ],
)
def test_flat_damage_proof_rejects_wrong_totals_pattern_or_unverified_context(item):
    contract, _ = HANDLERS['base'].contract(item, 'weapon')
    assert contract is None


def test_ambiguous_totals_require_owned_flat_damage_proof():
    item = weapon()
    capture = dict(item.provenance['capture'])
    capture.pop('superior_flat_damage')
    assert HANDLERS['base'].contract(replace(item, provenance={'capture': capture}), 'weapon')[0] is None
    dagger = replace(weapon('Dagger', 1, 5), provenance={'capture': capture})
    assert HANDLERS['base'].contract(dagger, 'weapon')[0] is not None
