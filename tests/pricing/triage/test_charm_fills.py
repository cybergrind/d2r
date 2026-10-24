"""Shimmering charms priced by completed trades (pricing/triage/charm_fills.py) and the triage taking that price."""

import pytest

from pricing.triage import charm_fills
from pricing.triage.charm_fills import band, facet_key, shape
from pricing.triage.engine import assess, prepare_tables


def trades(*prices, date='2026-10-20', seller=None):
    return {
        'trades': [
            {'date': date, 'ist': p, 'seller': seller or f's{i}', 'buyer': f'b{i}'} for i, p in enumerate(prices)
        ]
    }


def charm(properties, name='Small Charm'):
    return {'category': 'magic', 'name': name, 'rarity': 'magic', 'quantity': 1, 'properties': properties}


@pytest.mark.parametrize(
    ('name', 'properties', 'expected'),
    [
        ('Small Charm', {'441': 5, '418': 20}, ('sc', 5, '418', 20)),
        # A drop carries the four resistances beside 441; a read may carry the four alone
        ('Small Charm', {'441': 5, '401': 5, '426': 5, '427': 5, '428': 5, '461': 7}, ('sc', 5, '461', 7)),
        ('Large Charm', {'401': 8, '426': 8, '427': 8, '428': 8}, ('lc', 8, None, None)),
        ('Grand Charm', {'441': 15, '798': 'PC', '796': 42}, ('gc', 15, None, None)),
        ('Small Charm', {'427': 8, '418': 20}, None),  # one resistance: not shimmering
        ('Small Charm', {'441': 5, '418': 20, '461': 7}, None),  # two companions cannot roll on a magic charm
        ('Jewel', {'441': 10}, None),
    ],
)
def test_shape_reads_the_size_all_res_and_one_companion(name, properties, expected):
    assert shape(name, properties) == expected


def test_an_exact_facet_with_three_priced_trades_is_its_own_band():
    facets = {facet_key('sc', 5, '418', 20): trades(160.0, 162.4, 171.3, None)}
    found = band(charm({'441': 5, '418': 20}), facets)
    assert found is not None
    assert found['evidence_kind'] == 'fills'
    assert (found['fills'], found['median_ist'], found['bucket']) == (3, 162.4, 'fills:sc/5/418:20')
    assert 'fill_comparison' not in found


def test_a_thin_facet_is_priced_by_its_comparable_or_worse_trades_never_a_better_one():
    facets = {
        facet_key('sc', 5, '418', 19): trades(30.0),  # the item's own facet: one trade
        facet_key('sc', 4, '418', 16): trades(4.0, 5.0),
        facet_key('sc', 5, '418', 20): trades(160.0, 165.0, 170.0),  # better life: never prices a 19
        facet_key('sc', 5, '461', 7): trades(80.0, 80.0, 80.0),  # another companion
    }
    found = band(charm({'441': 5, '418': 19}), facets)
    assert found is not None
    assert sorted([found['min_ist'], found['max_ist']]) == [4.0, 30.0]
    assert found['fills'] == 3
    assert found['fill_comparison'] == '≤5 all res, 418 ≤19'


def test_plain_charms_are_a_floor_for_a_charm_with_a_suffix_but_not_the_other_way():
    facets = {facet_key('lc', 8, None, None): trades(0.6, 0.6), facet_key('lc', 7, None, None): trades(0.2)}
    assert (band(charm({'441': 8, '429': 3}, 'Large Charm'), facets) or {}).get('fills') == 3
    assert band(charm({'441': 8}, 'Large Charm'), {facet_key('lc', 8, '429', 3): trades(1.0, 1.0, 1.0)}) is None


def test_no_band_without_three_priced_trades():
    assert band(charm({'441': 5, '418': 20}), {facet_key('sc', 5, '418', 20): trades(160.0, None)}) is None


def test_liquid_needs_ten_trades_in_its_last_thirty_days():
    liquid, thin = (band(charm({'441': 4}), {'sc/4/plain': trades(*[1.0] * n)}) for n in (10, 9))
    assert (liquid or {}).get('liquidity') == 'liquid'
    assert (thin or {}).get('liquidity') == 'thin'


def tables(facets):
    return prepare_tables({'bands': []}, {'keep_ist': 0.25, 'rows': []}, {'rows': []}, facets)


def test_the_triage_prices_a_shimmering_charm_by_its_trades():
    item = charm({'441': 5, '418': 20, '401': 5, '426': 5, '427': 5, '428': 5})
    found = assess(item, tables({facet_key('sc', 5, '418', 20): trades(*[160.0, 162.4, 171.3] * 4)}))
    assert found['verdict'] == 'sell'
    assert found['band']['evidence_kind'] == 'fills'
    assert found['decision_ist'] == found['band']['median_ist']  # completed trades: the median decides
    assert found['reason'].startswith('sold ')


def test_the_median_of_the_trades_decides_the_keep_price_not_their_lower_quartile():
    found = assess(charm({'441': 8}, 'Large Charm'), tables({'lc/8/plain': trades(0.2, 0.2, 0.38, 0.6, 0.67)}))
    assert (found['verdict'], found['decision_ist']) == ('slow', 0.38)


def test_trades_under_the_keep_price_say_vendor():
    found = assess(charm({'441': 3}), tables({'sc/3/plain': trades(0.1, 0.2, 0.2)}))
    assert found['verdict'] == 'vendor'
    assert found['reason'].startswith('below keep price; sold ')


def test_no_fills_leave_the_triage_as_it_was():
    item = charm({'441': 5, '418': 20})
    assert assess(item, tables({}))['band'] is None
    assert charm_fills.facet({**item, 'quantity': 2}) is None
