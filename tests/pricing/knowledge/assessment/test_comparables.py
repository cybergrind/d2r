from copy import deepcopy
from datetime import date

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables


def contract():
    return {
        'version': 1,
        'policy': 'base',
        'family': 'weapon',
        'mode': 'exact_variant',
        'name': 'Cinquedeas',
        'rarity': 'superior',
        'ethereal': False,
        'sockets': 3,
        'socket_contents': 'empty',
        'properties': {'510': 15},
    }


def listing(seller='1', **changes):
    return {
        'name': 'Cinquedeas',
        'rarity': 'superior',
        'ethereal': False,
        'sockets': 3,
        'socket_contents': 'empty',
        'properties': {'510': 15},
        'evidence_kind': 'ask',
        'scope_status': 'verified',
        'seller_id': seller,
        'listing_id': seller,
        'unit_policy': 'single_item',
        'ask_ist': 2,
        'observed_at': '2026-09-24',
        **changes,
    }


def test_hard_facets_and_extra_premium_properties_exclude_false_comparables():
    bad = [
        listing('eth', ethereal=True),
        listing('unknown', ethereal=None),
        listing('filled', socket_contents='filled'),
        listing('unknownsocket', sockets=None),
        listing('ladder', scope_status='rejected'),
        listing('premium', properties={'510': 15, '423': 3}),
        listing('roll', properties={'510': 14}),
        listing('rarity', rarity='rare'),
    ]
    result = evaluate(contract(), [listing(), *bad])
    assert result['summary']['priced_sellers'] == 1
    assert len(result['rejected']) == len(bad)
    assert all(r['reasons'] for r in result['rejected'])


def test_only_dated_three_seller_comparables_produce_estimate():
    rows = [listing(str(i), ask_ist=i) for i in [1, 2, 3]]
    rows.append(listing('1', ask_ist=100, listing_id='another-listing-same-seller'))
    result = price_from_comparables(evaluate(contract(), rows), today=date(2026, 9, 24))
    assert result['estimate_ist'] == 2
    assert result['sellers'] == 3
    assert result['basis'] == 'classified_exact_variant_asks'
    thin = price_from_comparables(evaluate(contract(), rows[:2]), today=date(2026, 9, 24))
    assert thin['estimate_ist'] is None
    undated = deepcopy(rows[:3])
    undated[0]['observed_at'] = None
    result = price_from_comparables(evaluate(contract(), undated), today=date(2026, 9, 24))
    assert result['estimate_ist'] is None


def test_absent_contract_cannot_promote_a_name_level_band():
    result = evaluate(None, [listing()])
    assert result['summary']['priced_sellers'] == 0
    assert price_from_comparables(result)['estimate_ist'] is None


def test_listing_region_is_not_an_item_affix_and_does_not_relax_scope():
    scope = {'798': 'PC', '799': 'softcore', '800': False, '1854': 'reign of the warlock'}
    rows = [
        listing(str(i), ask_ist=i, properties={'510': 15, '933': region, **scope})
        for i, region in enumerate(('Americas', 'Europe', 'Asia'), 1)
    ]
    result = evaluate(contract(), rows)
    assert len(result['accepted']) == 3
    assert price_from_comparables(result, today=date(2026, 9, 24))['estimate_ist'] == 2
    for changed in ({'800': True}, {'798': 'PlayStation'}, {'799': 'hardcore'}, {'1854': 'resurrected'}, {'510': 14}):
        wrong = {**rows[0], 'properties': {**rows[0]['properties'], **changed}}
        assert not evaluate(contract(), [wrong])['accepted']
