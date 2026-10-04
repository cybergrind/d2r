from datetime import date

import pytest

from pricing.triage.engine import assess


def test_threshold_liquidity_staleness_and_own_use_are_separate():
    item = {'category': 'uniques', 'name': 'Example', 'properties': {}}
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {
            ('uniques', 'example', 'name'): {
                'median_ist': 0.25,
                'liquidity': 'liquid',
                'observed_at': '2026-08-01',
                'sellers': 10,
            }
        },
    }
    result = assess(item, tables, today=date(2026, 10, 3))
    assert result['verdict'] == 'slow'  # Seller activity alone is not endgame demand.
    assert result['stale'] is True
    tables['bands']['uniques', 'example', 'name']['liquidity'] = 'thin'
    assert assess(item, tables)['verdict'] == 'slow'
    tables['bands']['uniques', 'example', 'name']['median_ist'] = 0.24
    assert assess(item, tables)['verdict'] == 'vendor'
    tables['own']['rows'] = [{'category': 'uniques', 'name': 'Example', 'conditions': {}}]
    assert assess(item, tables)['verdict'] == 'self'


def test_required_property_unknown_does_not_match_premium_bucket():
    tables = {
        'rules': {
            'keep_ist': 0.25,
            'rows': [
                {
                    'category': 'uniques',
                    'name': 'Example',
                    'bucket': 'perfect',
                    'premium': True,
                    'properties': {'425': {'min': 120}},
                }
            ],
        },
        'own': {'rows': []},
        'bands': {},
    }
    item = {'category': 'uniques', 'name': 'Example', 'properties': {}}
    assert assess(item, tables)['verdict'] == 'check'
    assert assess({**item, 'properties': {'425': 120}}, tables)['verdict'] == 'sell'


def test_bulk_band_is_only_used_for_that_quantity():
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {
            ('runes', 'example', 'quantity:40'): {
                'median_ist': 0.5,
                'liquidity': 'thin',
                'observed_at': '2026-10-03',
            },
        },
    }
    item = {'category': 'runes', 'name': 'Example', 'quantity': 1}
    assert assess(item, tables)['band'] is None
    assert assess({**item, 'quantity': 40}, tables)['verdict'] == 'slow'
    assert assess({**item, 'quantity': 20}, tables)['band'] is None


def test_missing_named_variant_does_not_claim_ethereal_listings_are_absent():
    item = {
        'category': 'uniques',
        'name': 'Example',
        'properties': {},
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_code': 'native',
    }
    reference = {'median_ist': 1, 'separate_ethereal': True, 'separate_sockets': True, 'separate_base': True}
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('uniques', 'example', 'name'): reference},
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert (
        result['reason'] == 'no priced listings matching base, ethereal status and sockets; name band is reference only'
    )
    assert result['reference_band'] == reference
    unknown = assess(item | {'ethereal': None, 'sockets': None}, tables)
    assert (
        unknown['reason']
        == 'capture missing ethereal status, sockets; variant price unavailable; name band is reference only'
    )


def test_divisible_rune_stack_can_use_single_unit_sale_without_claiming_bulk_price():
    from inventory_tracking.appraisal.triage import headline

    unit = {
        'q1_ist': 9,
        'median_ist': 10,
        'sellers': 12,
        'liquidity': 'liquid',
        'quantity': 1,
        'observed_at': '2026-10-03',
    }
    lot = {'q1_ist': 15, 'median_ist': 15, 'sellers': 1, 'liquidity': 'none', 'quantity': 6}
    tables = {
        'rules': {'rows': [], 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {('runes', 'ber rune', 'name'): unit, ('runes', 'ber rune', 'quantity:6'): lot},
    }
    item = {'category': 'runes', 'name': 'Ber Rune', 'quantity': 6}
    result = assess(item, tables)
    assert result['verdict'] == 'sell'
    assert result['decision_ist'] == 9
    assert result['band'] == unit
    assert result['reference_band'] == lot
    assert 'each; sell individually' in headline(result)
    for category in ('sets', 'misc', 'base'):
        other = tables | {'bands': {(category, n, b): v for (_, n, b), v in tables['bands'].items()}}
        assert assess(item | {'category': category}, other)['verdict'] == ('check' if category == 'sets' else 'vendor')
    tables['bands']['runes', 'ber rune', 'quantity:6'] = lot | {'sellers': 4, 'liquidity': 'thin'}
    assert assess(item, tables)['band']['quantity'] == 6
    assert assess(item | {'quantity': 1}, tables).get('sale_mode') is None


def test_mixed_commodity_bundles_do_not_use_individual_unit_fallback():
    for category, name in [('runes', 'Rune Set'), ('gems', 'Random Gems')]:
        tables = {
            'rules': {'rows': [], 'keep_ist': 0.25},
            'own': {'rows': []},
            'bands': {(category, name.lower(), 'name'): {'q1_ist': 1, 'liquidity': 'liquid'}},
        }
        result = assess({'category': category, 'name': name, 'quantity': 5}, tables)
        assert result['verdict'] == 'vendor'
        assert result.get('sale_mode') is None


@pytest.mark.parametrize('category', ['uniques', 'sets', 'runewords'])
def test_named_missing_or_thin_evidence_is_check_not_vendor(category):
    from pricing.triage.engine import assess

    item = {'category': category, 'name': 'Example', 'properties': {}}
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    tables['bands'][(category, 'example', 'name')] = {
        'median_ist': 131,
        'q1_ist': 131,
        'sellers': 2,
        'liquidity': 'none',
    }
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert 'sellers' in result['reason']


@pytest.mark.parametrize('sellers', [1, 2, 3])
@pytest.mark.parametrize('price', [0.24, 0.25])
def test_paid_base_bucket_retains_sparse_variant_evidence(sellers, price):
    from pricing.triage.variants import scoped_bucket

    item = {'category': 'base', 'name': 'Example', 'sockets': 4, 'ethereal': True, 'properties': {}}
    policy = {'category': 'base', 'require_bucket': True, 'facets': ['sockets', 'ethereal']}
    band = {
        'median_ist': price,
        'q1_ist': price,
        'sellers': sellers,
        'liquidity': 'thin' if sellers >= 3 else 'none',
    }
    key = scoped_bucket('paid', item, policy['facets'])
    tables = {
        'rules': {
            'keep_ist': 0.25,
            'policies': [policy],
            'rows': [{'category': 'base', 'bucket': 'paid', 'conditions': {'sockets': 4, 'ethereal': True}}],
        },
        'own': {'rows': []},
        'bands': {('base', 'example', key): band},
    }
    result = assess(item, tables)
    assert result['band'] == band
    assert result['verdict'] == ('vendor' if price < 0.25 else 'slow' if sellers >= 3 else 'check')
    if price >= 0.25 and sellers < 3:
        assert 'fewer than three' in result['reason']
    # A sparse paid variant never lends its price to a different/unknown variant.
    for change in ({'sockets': None}, {'sockets': 0}, {'ethereal': False}):
        unmatched = assess(item | change, tables)
        assert unmatched['band'] is None
        assert unmatched['verdict'] == 'vendor'


def test_supported_gem_lot_uses_total_value_without_pricing_a_single_gem():
    from inventory_tracking.appraisal.triage import headline
    from pricing.triage.replay import listing_score
    from tests.pricing.triage.test_bands import listing

    band = {
        'q1_ist': 0.05,
        'median_ist': 0.05,
        'quantity': 20,
        'sellers': 3,
        'liquidity': 'thin',
        'observed_at': '2026-10-03',
    }
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('gems', 'perfect ruby', 'quantity:20'): band},
    }
    item = {'category': 'gems', 'name': 'Perfect Ruby', 'quantity': 20}
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1
    assert '1 Ist' in headline(result)
    assert 'lot of 20' in headline(result)
    assert '0.05 Ist each' in headline(result)
    assert assess(item | {'quantity': 1}, tables)['band'] is None
    assert assess(item | {'quantity': 10}, tables)['band'] is None
    rows = [
        listing(n, 0.05) | {'category': 'gems', 'name': 'Perfect Ruby', 'amount': 20, 'unit_policy': 'stack_total'}
        for n in range(3)
    ]
    score = listing_score(rows, tables)['categories']['gems']
    assert score['valuable'] == 3
    assert score.get('cheap', 0) == 0
    assert score['sell_recall'] == 1


def test_single_gem_is_check_to_save_for_a_supported_lot_not_a_single_unit_sale():
    from inventory_tracking.appraisal.triage import headline

    band = {
        'q1_ist': 1 / 15,
        'median_ist': 1 / 15,
        'quantity': 15,
        'sellers': 5,
        'liquidity': 'thin',
        'observed_at': '2026-10-03',
    }
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('gems', 'perfect ruby', 'quantity:15'): band},
    }
    item = {'category': 'gems', 'name': 'Perfect Ruby', 'quantity': 1}
    result = assess(item, tables)
    assert result['verdict'] == 'check'
    assert result['band'] is None
    assert result['decision_ist'] is None
    assert result['reference_band'] == band
    assert 'save toward a lot of 15' in headline(result)
    assert '1 Ist' in headline(result)
    assert '2026-10-03' in headline(result)
    assert assess(item | {'quantity': 15}, tables)['verdict'] == 'slow'
    assert assess(item | {'name': 'Random Gems'}, tables)['verdict'] == 'vendor'
    tables['bands'][('gems', 'perfect ruby', 'quantity:15')] = band | {'sellers': 2, 'liquidity': 'none'}
    assert assess(item, tables)['verdict'] == 'vendor'


def test_larger_commodity_holding_can_supply_a_supported_lot_without_extrapolating_price():
    from inventory_tracking.appraisal.triage import headline

    band = {
        'q1_ist': 1 / 15,
        'quantity': 15,
        'sellers': 5,
        'liquidity': 'thin',
        'observed_at': '2026-10-03',
    }
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {('gems', 'perfect ruby', 'quantity:15'): band},
    }
    item = {'category': 'gems', 'name': 'Perfect Ruby', 'quantity': 32}
    result = assess(item, tables)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 1  # Quote one sale lot, not the entire holding.
    assert result['sale_mode'] == 'split_bulk'
    assert 'sell in lots of 15' in headline(result)
    assert '1 Ist' in headline(result)
    assert '2026-10-03' in headline(result)
    assert assess(item | {'quantity': 14}, tables)['verdict'] == 'check'
    for quantity in (None, '32', 0):
        assert assess(item | {'quantity': quantity}, tables)['verdict'] == 'vendor'
    assert assess(item | {'name': 'Random Gems'}, tables)['verdict'] == 'vendor'
    tables['bands'][('gems', 'perfect ruby', 'quantity:15')] = band | {'sellers': 2, 'liquidity': 'none'}
    assert assess(item, tables)['verdict'] == 'vendor'
