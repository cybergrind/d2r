from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def shaftstop_contract():
    item = facts('Boneweave', 'unique', 'Shaftstop').to_dict()
    item['ethereal'] = True
    rows, affixes, unresolved = decode_stats(
        [{'id': k, 'layer': 0, 'raw': v} for k, v in ((16, 220), (31, 2374), (32, 250), (36, 30), (7, 15360))]
    )
    item['affixes'] = affixes
    capture = normalize(
        {
            'item': item,
            'decoded_stats': rows,
            'unresolved_stats': unresolved,
            'source': {
                'stat_capture_complete': True,
                'item_identity': {
                    'table': 'unique',
                    'table_id': named_definitions()['unique', 'Shaftstop']['table_id'],
                },
            },
        }
    )
    contract, gaps = NamedHandler().contract(capture, 'armor')
    assert not gaps
    return contract.to_dict()


def listing(upgraded, *, include_tier=True):
    properties = {
        '799': 'softcore',
        '800': False,
        '798': 'PC',
        '1854': 'reign of the warlock',
        '738': True,
        '402': 0,
        '934': '',
        '930': 'Elite',
        '1216': upgraded,
        '425': 220,
        '1855': 2374,
    }
    if not include_tier:
        properties.pop('930')
    raw = {
        'id': 'fixture',
        'seller_id': 'seller',
        'amount': 1,
        'active': True,
        'selling': True,
        'completed': False,
        'prices': [{'name': 'Ist Rune', 'quantity': 10}],
        'properties': [
            {
                'property_id': k,
                'type': 'bool' if type(v) is bool else 'number' if type(v) is int else 'string',
                'bool' if type(v) is bool else 'number' if type(v) is int else 'string': v,
            }
            for k, v in properties.items()
        ],
    }
    return normalize_listing(
        raw, name='Shaftstop', category='uniques', source='fixture', observed_at='2026-09-24', currencies={'ist': 1}
    )


def test_upgraded_listing_matches_complete_capture_with_fixed_bonuses_omitted():
    row = listing(True)
    result = evaluate(shaftstop_contract(), [row])
    assert result['accepted'] == [row], result['rejected']
    for value in (False, 1, 'yes'):
        bad = listing(value)
        assert not evaluate(shaftstop_contract(), [bad])['accepted']


def test_variable_defense_and_ed_still_have_to_match():
    contract = shaftstop_contract()
    for prop, value in [('1855', 2300), ('425', 219)]:
        row = listing(True)
        row['properties'][prop] = value
        assert not evaluate(contract, [row])['accepted']


def test_explicit_upgrade_flag_without_tier_reaches_exact_scoped_price_gate():
    from datetime import date

    from pricing.knowledge.assessment.comparables import price_from_comparables

    rows = []
    for seller, price in enumerate((9, 10, 11)):
        row = listing(True, include_tier=False)
        row.update(seller_id=str(seller), listing_id=str(seller), ask_ist=price)
        rows.append(row)
    comparisons = evaluate(shaftstop_contract(), rows)
    assert len(comparisons['accepted']) == 3, comparisons['rejected']
    assert price_from_comparables(comparisons, today=date(2026, 9, 24))['estimate_ist'] == 10
    for prop, value in [('425', 219), ('1855', 2300)]:
        bad = listing(True, include_tier=False)
        bad['properties'][prop] = value
        assert not evaluate(shaftstop_contract(), [bad])['accepted']
