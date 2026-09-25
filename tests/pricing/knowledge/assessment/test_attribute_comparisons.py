import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_comparables import listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


ATTRIBUTES = ('437', '429', '582', '421')


def annihilus_contract():
    item = facts('Small Charm', 'unique', 'Annihilus').to_dict()
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': stat, 'layer': 0, 'raw': value}
            for stat, value in [
                (0, 20),
                (1, 20),
                (2, 20),
                (3, 20),
                (39, 20),
                (41, 20),
                (43, 20),
                (45, 20),
                (85, 10),
                (127, 1),
            ]
        ]
    )
    assert not unresolved
    capture = normalize(
        {'item': {**item, 'affixes': affixes}, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}
    )
    contract, gaps = NamedHandler().contract(capture, 'charm')
    assert contract is not None, gaps
    return contract.to_dict()


def observation(properties):
    return listing(name='Annihilus', rarity='unique', sockets=0, properties=properties) | {
        'base_code': facts('Small Charm').base_code
    }


def test_native_annihilus_attributes_match_combined_listing_without_losing_other_rolls():
    contract = annihilus_contract()
    expanded = dict(contract['properties'])
    assert all(expanded[key] == 20 for key in ATTRIBUTES)
    combined = {key: value for key, value in expanded.items() if key not in ATTRIBUTES} | {'727': 20}
    assert evaluate(contract, [observation(combined)])['accepted']
    assert evaluate(contract | {'properties': combined}, [observation(expanded)])['accepted']
    assert not evaluate(contract, [observation(combined | {'727': 19})])['accepted']
    assert not evaluate(contract, [observation(expanded | {'437': 21})])['accepted']


@pytest.mark.parametrize('extra', [{'437': 20}, {'727': True}, {'727': '20'}, {'727': float('nan')}])
def test_ambiguous_or_invalid_all_attribute_values_do_not_match(extra):
    contract = annihilus_contract()
    properties = {k: v for k, v in contract['properties'].items() if k not in ATTRIBUTES} | {'727': 20} | extra
    assert not evaluate(contract, [observation(properties)])['accepted']


def test_combined_attribute_and_resistance_asks_reach_price_with_exact_rolls():
    from datetime import date

    from pricing.knowledge.assessment.comparables import price_from_comparables

    contract = annihilus_contract()
    resists = ('427', '428', '426', '401')
    properties = {k: v for k, v in contract['properties'].items() if k not in (*ATTRIBUTES, *resists)}
    properties |= {'727': 20, '441': 20}
    rows = [observation(properties) | {'seller_id': str(i), 'listing_id': str(i), 'ask_ist': i} for i in (1, 2, 3)]
    result = price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 24))
    assert result['estimate_ist'] == 2
    assert result['sellers'] == 3
    assert all(row['properties'] == properties for row in rows)
