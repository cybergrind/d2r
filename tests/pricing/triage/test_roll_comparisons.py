import pytest

from pricing.triage.roll_comparisons import compare, deciding_stats, leave_one_out, validation_summary


def rows():
    return [
        {
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 0.2 if i == 0 else 1,
            'properties': {'skill': 2 if i == 0 else 3, 'ed': 50 + i % 11},
        }
        for i in range(19)
    ]


RANGES = {
    'skill': {'min': 1, 'max': 3, 'label': 'Vengeance', 'better': 'higher'},
    'ed': {'min': 50, 'max': 60, 'label': 'enhanced damage', 'better': 'higher'},
}


def test_thin_cohort_keeps_worse_roll_asks_instead_of_using_cheapest_exact_copy():
    listings = [
        {'seller_id': 'one', 'ask_ist': 0.789, 'properties': {'skill': 1}},
        {'seller_id': 'two', 'ask_ist': 0.2, 'properties': {'skill': 2}},
        {'seller_id': 'three', 'ask_ist': 11.4, 'properties': {'skill': 3}},
    ]
    result = compare({'skill': 2}, listings, {'skill': RANGES['skill']}, keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['sellers'] == 2
    assert result['q1_ist'] == pytest.approx(0.34725)


def test_selection_detects_paid_skill_not_evenly_distributed_ed():
    selected = deciding_stats(rows(), RANGES)
    assert set(selected) == {'skill'}
    assert selected['skill']['top_count'] == 18
    assert selected['skill']['sample_size'] == 19
    low = compare({'skill': 2, 'ed': 50}, rows(), selected, keep_ist=0.25)
    assert low['verdict'] == 'check'
    assert low['q1_ist'] == 0.2
    assert low['sellers'] == 1
    assert 'Vengeance' in low['reason']
    high = compare({'skill': 3, 'ed': 50}, rows(), selected, keep_ist=0.25)
    assert high['sellers'] == 19


def test_missing_roll_and_below_every_listed_roll_never_sell():
    selected = deciding_stats(rows(), RANGES)
    assert compare({}, rows(), selected, keep_ist=0.25)['verdict'] == 'check'
    low = compare({'skill': 1}, rows()[1:], selected, keep_ist=0.25)
    assert low['verdict'] == 'check'
    assert low['upper_bound_ist'] == 1
    assert low['q1_ist'] is None


def test_comparables_must_be_no_better_on_every_deciding_stat():
    selected = {p: {'min': 1, 'max': 10, 'label': p, 'better': 'higher'} for p in ('a', 'b')}
    listings = [
        {'seller_id': str(i), 'ask_ist': price, 'properties': props}
        for i, (price, props) in enumerate(
            [(1, {'a': 2, 'b': 2}), (100, {'a': 1, 'b': 9}), (100, {'a': 9, 'b': 1}), (100, {'a': 2})]
        )
    ]
    result = compare({'a': 3, 'b': 3}, listings, selected, keep_ist=0.25)
    assert result['sellers'] == 1
    assert result['q1_ist'] == 1
    assert result['verdict'] == 'check'


def test_leave_one_out_excludes_all_copies_from_the_held_out_seller():
    listings = rows()
    listings.append({**listings[0], 'listing_id': 'duplicate'})
    report = leave_one_out(listings, deciding_stats(listings, RANGES))
    assert report['evaluated'] > 0
    assert report['seller_exclusion'] is True
    assert report['roll_median_error'] is not None
    assert report['name_median_error'] is not None


def test_out_of_range_drop_cannot_be_priced_as_a_perfect_roll():
    selected = deciding_stats(rows(), RANGES)
    result = compare({'skill': 4}, rows(), selected, keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['q1_ist'] is None
    assert 'outside native range' in result['reason']


def test_invalid_listed_roll_cannot_supply_a_cheap_upper_bound():
    selected = {'skill': RANGES['skill']}
    listings = [{'seller_id': 'bad', 'ask_ist': 0.01, 'properties': {'skill': 4}}]
    result = compare({'skill': 1}, listings, selected, keep_ist=0.25)
    assert result['verdict'] == 'check'
    assert result['upper_bound_ist'] is None


def test_held_out_seller_cannot_supply_the_stat_selection_sample():
    listings = rows()[:15]
    selected = deciding_stats(listings, RANGES)
    assert selected
    report = leave_one_out(listings, selected, ranges=RANGES)
    assert report['selection_recomputed'] is True
    assert report['evaluated'] == 0
    assert report['use_roll_model'] is False


def test_aggregate_validation_weights_held_out_sellers_and_lists_fallbacks():
    reports = [
        {
            'name': 'A',
            'ethereal': False,
            'socket_contents': 'empty',
            'validation': {'paired_errors': [(1, 2)] * 3, 'roll_median_error': 1, 'name_median_error': 2},
        },
        {
            'name': 'B',
            'ethereal': False,
            'socket_contents': 'empty',
            'validation': {'paired_errors': [(10, 3)], 'roll_median_error': 10, 'name_median_error': 3},
        },
    ]
    result = validation_summary(reports)
    assert result['evaluated'] == 4
    assert result['roll_median_error'] == 1
    assert result['name_median_error'] == 2
    assert [row['name'] for row in result['fallbacks']] == ['B']


@pytest.mark.parametrize(('sellers', 'expected'), [(1, 'check'), (2, 'check'), (3, 'vendor')])
def test_cheap_comparable_rolls_need_three_sellers_before_vendor(sellers, expected):
    listings = [{'seller_id': str(i), 'ask_ist': 0.2, 'properties': {'skill': 2}} for i in range(sellers)]
    result = compare({'skill': 2}, listings, {'skill': RANGES['skill']}, keep_ist=0.25)
    assert result['verdict'] == expected
    assert result['sellers'] == sellers
    assert result['q1_ist'] == pytest.approx(0.2)
