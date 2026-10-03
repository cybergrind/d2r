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


def test_new_captures_are_reported_without_claiming_legacy_agreement():
    from pricing.triage.replay import compare_types

    item = {'id': 'new', 'observation': {'item': {'name': 'Ring', 'base_name': 'Ring', 'rarity': 'rare'}}}
    report = compare_types([item], [{'id': 'new', 'verdict': 'check'}], [], keep_ist=0.25)
    group = next(iter(report.values()))
    assert group['triage'] == {'check': 1}
    assert group['without_legacy'] == ['new']
    assert not group['legacy']
    assert not group['lost_attention']
