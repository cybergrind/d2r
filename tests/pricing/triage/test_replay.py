import pytest

from pricing.triage.replay import listing_score
from tests.pricing.triage.test_bands import listing


@pytest.mark.parametrize('category', ['rare', 'magic', 'crafted', 'uniques'])
def test_check_counts_as_affixed_attention_but_cheap_checks_are_reported(category):
    rule = {'category': category, 'pattern': {'properties': {'520': {'min': 10}}}}
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': [rule]}, 'own': {'rows': []}}
    rows = [listing('valuable', 1), listing('cheap', 0.01)]
    for row in rows:
        row.update(category=category, rarity=category)
        row['properties']['520'] = 10
    report = listing_score(rows, tables)['categories'][category]
    assert report['recall'] == (None if category == 'uniques' else 1)
    assert report['sell_recall'] == (None if category == 'uniques' else 0)
    assert report['cheap_false_positive_rate'] == 0
    assert report['cheap_check_rate'] == 1


@pytest.mark.parametrize(
    ('change', 'accepted'),
    [
        ({}, True),
        ({'band': {'q1_ist': 0.25, 'sellers': 10}}, False),
        ({'band': {'q1_ist': 0.2, 'sellers': 2}}, False),
        ({'band': None, 'reference_band': {'q1_ist': 0.2, 'sellers': 10}}, False),
    ],
)
def test_named_below_threshold_correction_requires_matched_price_evidence(change, accepted):
    from pricing.triage.replay import compare_types
    from tests.pricing.triage.test_capture_mechanics import observation

    capture = observation('uap', ethereal=False, sockets=0, socket_contents='empty')
    result = {'id': 'one', 'verdict': 'vendor', 'band': {'q1_ist': 0.2, 'sellers': 10}} | change
    report = compare_types(
        [{'id': 'one', 'observation': capture}],
        [result],
        [{'id': 'one', 'verdict': 'keep'}],
        keep_ist=0.25,
    )['uniques/helm']
    assert len(report['accepted_corrections']) == int(accepted)
    assert len(report['lost_attention']) == int(not accepted)


def test_unknown_capture_variant_cannot_pass_rollout_as_cheap_correction():
    from pricing.triage.replay import compare_types
    from tests.pricing.triage.test_capture_mechanics import observation

    report = compare_types(
        [{'id': 'one', 'observation': observation('uap')}],
        [{'id': 'one', 'verdict': 'vendor', 'band': {'q1_ist': 0.2, 'sellers': 10}}],
        [{'id': 'one', 'verdict': 'keep'}],
        keep_ist=0.25,
    )['uniques/helm']
    assert len(report['lost_attention']) == 1
    assert report['accepted_corrections'] == []


def test_named_recall_excludes_high_asks_on_a_cheap_cohort():
    from pricing.triage.bands import build_bands

    rows = [listing(str(i), price) for i, price in enumerate([0.1, 0.1, 0.1, 10])]
    doc = build_bands(rows, [])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
    }
    result = listing_score(rows, tables)['categories']['uniques']
    assert result['valuable'] == 0
    assert result['asks_above_cheap_cohort'] == 1
    assert result['recall'] is None


def test_a_cheap_ask_is_a_false_flag_only_when_under_nine_in_ten_sellers_ask_the_keep_price():
    from pricing.triage.bands import build_bands

    def score(prices):
        rows = [listing(str(i), price) for i, price in enumerate(prices)]
        doc = build_bands(rows, [])
        tables = {
            'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
            'rules': {'keep_ist': 0.25, 'rows': []},
            'own': {'rows': []},
        }
        return listing_score(rows, tables)['categories']['uniques']

    low = score([0.01] + [10] * 9)
    assert (low['cheap'], low['flagged_cheap'], low['underpriced_in_valuable_cohort']) == (1, 0, 1)
    assert low['cheap_false_positive_rate'] == 0
    mixed = score([0.01, 0.01] + [10] * 8)
    assert (mixed['cheap'], mixed['flagged_cheap']) == (2, 2)
    assert 'underpriced_in_valuable_cohort' not in mixed


def test_new_captures_are_reported_without_claiming_legacy_agreement():
    from pricing.triage.replay import compare_types

    item = {'id': 'new', 'observation': {'item': {'name': 'Ring', 'base_name': 'Ring', 'rarity': 'rare'}}}
    report = compare_types([item], [{'id': 'new', 'verdict': 'check'}], [], keep_ist=0.25)
    group = next(iter(report.values()))
    assert group['triage'] == {'check': 1}
    assert group['without_legacy'] == ['new']
    assert not group['legacy']
    assert not group['lost_attention']


def test_seller_score_deduplicates_stock_within_pattern_and_keeps_listing_score():
    rule = {'category': 'rare', 'pattern': {'properties': {'520': {'min': 10}}}}
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': [rule]}, 'own': {'rows': []}}
    rows = []
    for i in range(20):
        row = listing(str(i), 1)
        row.update(category='rare', rarity='rare', name='Amulet', seller_id='bulk')
        rows.append(row)
    good = listing('good', 1)
    good.update(category='rare', rarity='rare', name='Amulet')
    good['properties']['520'] = 10
    result = listing_score([*rows, good], tables)
    assert result['overall']['priced'] == 2
    assert result['overall']['recall'] == 0.5
    assert result['per_listing']['overall']['priced'] == 21
    assert result['per_listing']['overall']['recall'] == 1 / 21


def test_seller_score_uses_lowest_ask_and_does_not_combine_different_patterns():
    rules = [{'category': 'rare', 'pattern': {'properties': {p: {'min': 10}}}} for p in ('520', '418')]
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': rules}, 'own': {'rows': []}}
    rows = []
    for i, (prop, price) in enumerate([('520', 1), ('520', 0.01), ('418', 1)]):
        row = listing(str(i), price)
        row.update(category='rare', rarity='rare', name='Amulet', seller_id='same')
        row['properties'][prop] = 10
        rows.append(row)
    result = listing_score(rows, tables)
    assert result['overall']['priced'] == 2
    assert result['overall']['valuable'] == 1
    assert result['overall']['cheap'] == 1
    assert result['overall']['cheap_check_rate'] == 1
    assert result['per_listing']['overall']['valuable'] == 2


def test_seller_score_preserves_ethereal_cohorts_and_excludes_unknown_sellers():
    from pricing.triage.bands import build_bands

    rows = [listing('one', 1), listing('two', 2), listing('missing', 3)]
    rows[1].update(seller_id='one', ethereal=True)
    rows[2]['seller_id'] = None
    doc = build_bands(rows, [])
    tables = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in doc['bands']},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
    }
    result = listing_score(rows, tables)
    assert result['overall']['priced'] == 2
    assert result['missing_seller_listings'] == 1
    assert result['per_listing']['overall']['priced'] == 3


def test_miss_causes_rank_distinct_sellers_not_duplicate_stock():
    data = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}}
    rows = []
    for name, seller, copies in [('Amulet', 'bulk', 20), ('Ring', 'a', 1), ('Ring', 'b', 1)]:
        for i in range(copies):
            rows.append(
                listing(f'{seller}-{i}', 1) | {'category': 'rare', 'rarity': 'rare', 'name': name, 'seller_id': seller}
            )
    report = listing_score(rows, data)
    causes = report['miss_causes']['rare']
    assert causes[0]['family'] == 'ring'
    assert causes[0]['distinct_sellers'] == 2
    assert causes[0]['seller_votes'] == 2
    assert causes[1]['family'] == 'amul'
    assert causes[1]['listings'] == 20
    assert causes[1]['distinct_sellers'] == 1
    assert causes[1]['cause'] == 'no_paid_pattern'
    assert sum(c['seller_votes'] for c in causes) == report['overall']['valuable']


def test_unknown_rarity_listing_is_a_data_gap_not_a_missing_base_rule():
    row = listing('unknown', 1) | {'category': 'base', 'name': 'Gauntlets', 'sockets': 0}
    data = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}}
    result = listing_score([row], data)
    assert result['miss_causes']['base'][0]['cause'] == 'base_rarity_missing'
    assert result['overall']['valuable'] == 1
