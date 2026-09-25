from copy import deepcopy
from datetime import date

import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_comparables import listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('Cold Rupture', '21102838', 187, 43, '426', 70),
    ('Flame Rift', '1363635173', 189, 39, '427', 70),
    ('Crack of the Heavens', '849307965', 190, 41, '428', 70),
    ('Rotting Fissure', '1283013862', 191, 45, '401', 70),
    ('Bone Break', '374110750', 192, 36, '1223', 10),
    ('Black Cleft', '1731212580', 193, 37, '936', 45),
]


def comparison(case):
    name, catalog_id, effect, penalty, prop, magnitude = case
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': effect, 'layer': 0, 'raw': 300},
            {'id': penalty, 'layer': 0, 'raw': -magnitude},
        ]
    )
    item = facts('Grand Charm', 'unique', name)
    captured = normalize(
        {
            'item': {**item.to_dict(), 'affixes': affixes},
            'decoded_stats': decoded,
            'unresolved_stats': unresolved,
            'source': {'stat_capture_complete': True},
        }
    )
    contract, gaps = NamedHandler().contract(captured, 'charm')
    assert not gaps
    row = listing(
        name=name,
        catalog_id=catalog_id,
        rarity='unique',
        base_code=item.base_code,
        sockets=0,
        properties={prop: magnitude},
    )
    return contract.to_dict(), row


@pytest.mark.parametrize('case', CASES, ids=[c[0] for c in CASES])
def test_original_sunder_listing_penalty_magnitude_matches_captured_negative(case):
    contract, row = comparison(case)
    original = deepcopy(row)
    result = evaluate(contract, [row])
    assert result['accepted'] == [row], result['rejected']
    assert row == original
    wrong = {**row, 'properties': {case[4]: case[5] + 1}}
    assert not evaluate(contract, [wrong])['accepted']


@pytest.mark.parametrize(
    'change',
    [
        {'catalog_id': 'unknown'},
        {'properties': {'427': 69}},
        {'properties': {'427': 70.5}},
        {'properties': {'427': True}},
        {'name': 'Renewed Flame Rift'},
        {'properties': {'427': 70, '1872': 1}},
    ],
)
def test_unverified_sunder_variant_or_payload_cannot_match(change):
    contract, row = comparison(CASES[1])
    assert not evaluate(contract, [{**row, **change}])['accepted']


def test_bone_break_conflicting_damage_fields_are_not_collapsed():
    contract, row = comparison(CASES[4])
    row['properties']['1865'] = -10
    assert not evaluate(contract, [row])['accepted']


def test_undated_sunder_matches_do_not_create_a_price():
    contract, row = comparison(CASES[1])
    rows = [{**row, 'seller_id': str(i), 'listing_id': str(i), 'observed_at': None} for i in range(3)]
    result = evaluate(contract, rows)
    assert len(result['accepted']) == 3
    assert price_from_comparables(result, today=date(2026, 9, 25))['estimate_ist'] is None


def test_ordinary_resistances_keep_their_sign():
    contract, row = comparison(CASES[1])
    contract.update(name='Grand Charm', policy='affixed', rarity='magic', properties={'427': -70})
    contract.pop('intrinsic_properties', None)
    row.update(name='Grand Charm', rarity='magic')
    assert not evaluate(contract, [row])['accepted']
    row['properties']['427'] = -70
    assert evaluate(contract, [row])['accepted'] == [row]


def test_signed_sunder_resistance_is_also_exact_and_illegal_capture_is_rejected():
    contract, row = comparison(CASES[1])
    row['properties']['427'] = -70
    assert evaluate(contract, [row])['accepted'] == [row]
    contract['properties']['427'] = -100
    row['properties']['427'] = 100
    assert not evaluate(contract, [row])['accepted']
