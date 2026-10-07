import pytest

from pricing.triage.market_demand import qualify


@pytest.mark.parametrize(
    ('observation', 'guide', 'expected'),
    [
        ({'previous_listings': 10, 'current_listings': 10, 'disappeared': 0}, False, 'vendor'),
        ({'previous_listings': 10, 'current_listings': 10, 'disappeared': 0}, True, 'slow'),
        ({'previous_listings': 10, 'current_listings': 9, 'disappeared': 1}, False, 'vendor'),
        ({'previous_listings': 10, 'current_listings': 9, 'uncensored_disappeared': 1}, False, 'slow'),
        (
            {'previous_listings': 10, 'current_listings': 9, 'disappeared': 1, 'censored_disappeared': 1},
            False,
            'vendor',
        ),
        ({'buyers': 1}, False, 'slow'),
        (None, False, 'slow'),
        ({'previous_listings': 0, 'current_listings': 10, 'disappeared': 0}, False, 'slow'),
    ],
)
def test_cheap_equipment_uses_demand_but_missing_measurements_are_not_inactivity(observation, guide, expected):
    verdict, _ = qualify('sell', 0.5, guide, observation)
    assert verdict == expected


def test_above_one_ist_still_needs_demand_for_green_sell():
    assert qualify('sell', 2, False, None)[0] == 'slow'
    assert qualify('sell', 2, True, None)[0] == 'sell'
    assert qualify('sell', 2, False, {'buyers': 1})[0] == 'sell'
    assert qualify('check', None, True, {'buyers': 1})[0] == 'check'
    assert qualify('vendor', 0.1, True, {'buyers': 1})[0] == 'vendor'


def test_published_measurement_changes_engine_verdict_without_losing_own_use():
    from pricing.triage.engine import assess, prepare_tables
    from pricing.triage.listing_scores import cohort_key

    item = {'category': 'uniques', 'name': 'Example', 'properties': {}, 'ethereal': False}
    band = {
        'category': 'uniques',
        'name': 'Example',
        'bucket': 'name',
        'q1_ist': 0.5,
        'median_ist': 0.6,
        'sellers': 10,
        'liquidity': 'liquid',
    }
    document = {'bands': [band]}
    rules, own = {'keep_ist': 0.25, 'rows': []}, {'rows': []}
    tables = prepare_tables(document, rules, own)
    old = assess(item, tables)
    key = cohort_key(item, old, band, tables)
    document['market_demand'] = {
        'complete': True,
        'cohorts': {key: {'previous_listings': 10, 'current_listings': 10, 'disappeared': 0}},
        'buyers': {},
    }
    tables = prepare_tables(document, rules, own)
    assert assess(item, tables)['verdict'] == 'vendor'
    assert assess(item, tables)['decision_ist'] == 0.5
    own['rows'] = [{'category': 'uniques', 'name': 'Example'}]
    assert assess(item, tables)['verdict'] == 'slow'
    own['rows'] = []
    tables['market_demand']['buyers'][key] = {'buyers': 1}
    assert assess(item, tables)['verdict'] == 'slow'


def test_agreement_keeps_unmeasured_sell_cohorts_and_censored_absence_visible():
    from pricing.triage.market_demand import agreement

    measured = {
        'cohorts': {
            'active': {'disappeared': 10, 'uncensored_disappeared': 0, 'previous_listings': 20},
            'strong': {'disappeared': 4, 'uncensored_disappeared': 4, 'previous_listings': 10},
        },
        'buyers': {'cohorts': {}},
    }
    result = agreement({'active': ['sell', 'vendor'], 'missing': ['sell'], 'strong': ['vendor']}, measured)
    assert result['sell_cohorts'] == 2
    assert result['sell_supported_share'] == 0
    assert result['sell_supported_only_by_censored_absence'] == 1
    assert result['sell_unmeasured'] == ['missing']
    assert result['vendor_strong_share'] == 0.5


def test_vendor_with_above_threshold_asks_explains_missing_demand_in_headline():
    from inventory_tracking.appraisal.triage import headline

    text = headline(
        {
            'verdict': 'vendor',
            'reason': 'asks 0.5 Ist; no build use, turnover or observed buyers',
            'band': {'q1_ist': 0.5, 'median_ist': 0.6, 'sellers': 10, 'observed_at': '2026-10-04'},
            'keep_ist': 0.25,
            'decision_ist': 0.5,
        }
    )
    assert 'no build use, turnover or observed buyers' in text
