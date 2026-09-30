"""Fixed jewelry audits preserve named identity and refuse variable-roll additions."""

from datetime import date

import pytest


def test_fixed_jewelry_audit_has_exact_contracts_and_no_invented_prices():
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import audit

    rows = audit([], date(2026, 9, 29))
    assert {r['name'] for r in rows} == {'The Stone of Jordan', "The Cat's Eye", 'The Mahim-Oak Curio', "Atma's Scarab"}
    for row in rows:
        assert row['contract']['policy'] == 'named'
        assert row['contract']['rarity'] == 'unique'
        assert row['contract']['ethereal'] is False
        assert row['disposition'] == 'evidence_unavailable'
        assert row['price']['estimate_ist'] is None
        assert row['cached_observations'] == 0
    soj = next(r for r in rows if r['name'] == 'The Stone of Jordan')
    assert soj['contract']['intrinsic_properties']


def test_variable_jewelry_cannot_enter_fixed_price_audit():
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import template_contract

    with pytest.raises(ValueError, match='reviewed fixed'):
        template_contract("Mara's Kaleidoscope")


def test_reviewed_fixed_values_must_still_match_native_definitions(monkeypatch):
    from pricing.knowledge.assessment.maintenance import fixed_jewelry_market_review as review

    monkeypatch.setitem(review.SPECS, 'The Stone of Jordan', {9: 21, 77: 25, 50: 1, 51: 12, 127: 1})
    with pytest.raises(ValueError, match='definition changed'):
        review.template_contract('The Stone of Jordan')


def test_cached_review_separates_supported_asks_from_absent_evidence():
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import build_review
    from pricing.knowledge.assessment.maintenance.inventory import ROOT

    review = build_review(ROOT, date(2026, 9, 29))
    rows = {r['name']: r for r in review['rows']}
    soj = rows['The Stone of Jordan']
    assert soj['disposition'] == 'estimate'
    assert soj['price']['sellers'] >= 3
    assert soj['price']['basis'] == 'classified_exact_variant_asks'
    assert 'pricing/raw/traderie/wpi-the-stone-of-jordan.json' in review['inputs']
    for name in ("The Cat's Eye", 'The Mahim-Oak Curio'):
        assert rows[name]['cached_observations'] == 0
        assert rows[name]['price']['unavailable_reason'] == 'no_matches'


def test_fixed_jewelry_review_only_closes_matching_native_unique_identity():
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import apply_reviews, build_review
    from pricing.knowledge.assessment.maintenance.inventory import ROOT

    review = build_review(ROOT, date(2026, 9, 29))
    rows = [
        {
            'kind': kind,
            'name': name,
            'category': quality,
            'catalog_ids': ids,
            'dimensions': {'discovery': {'state': state}, 'market': {'state': 'pending'}},
        }
        for kind, name, quality, ids, state in (
            ('identity', 'The Stone of Jordan', 'unique', ['unique122'], 'reviewed'),
            ('identity', "The Cat's Eye", 'unique', ['unique269'], 'reviewed'),
            ('identity', 'The Mahim-Oak Curio', 'unique', ['unique119'], 'reviewed'),
            ('identity', "Atma's Scarab", 'unique', ['unique273'], 'reviewed'),
            ('identity', 'The Stone of Jordan', 'unique', ['unique999'], 'reviewed'),
            ('identity', 'The Stone of Jordan', 'unique', ['unique122', 'unique999'], 'reviewed'),
            ('identity', 'The Stone of Jordan', 'set', ['unique122'], 'reviewed'),
            ('role', 'The Stone of Jordan', 'unique', ['unique122'], 'reviewed'),
            ('identity', 'The Stone of Jordan', 'unique', ['unique122'], 'blocked'),
            ('identity', 'Ring', 'base', ['rin'], 'reviewed'),
        )
    ]
    apply_reviews(rows, review, ROOT)
    assert [r['dimensions']['market']['state'] for r in rows] == ['reviewed'] * 4 + ['pending'] * 6
    assert rows[0]['dimensions']['market']['disposition'] == 'estimate'
    assert rows[1]['dimensions']['market']['disposition'] == 'evidence_unavailable'


@pytest.mark.parametrize('mutation', ['price', 'missing-row', 'extra-row', 'missing-pin', 'stale-pin', 'scope'])
def test_fixed_jewelry_review_rejects_changed_or_incomplete_evidence(mutation):
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import apply_reviews, build_review
    from pricing.knowledge.assessment.maintenance.inventory import ROOT

    review = build_review(ROOT, date(2026, 9, 29))
    if mutation == 'price':
        review['rows'][0]['price']['estimate_ist'] = 99999
    elif mutation == 'missing-row':
        review['rows'].pop()
    elif mutation == 'extra-row':
        review['rows'].append(review['rows'][0])
    elif mutation == 'missing-pin':
        review['inputs'].pop(next(iter(review['inputs'])))
    elif mutation == 'stale-pin':
        review['inputs'][next(iter(review['inputs']))] = 'stale'
    else:
        review['scope'] = 'all_unique_items'
    with pytest.raises(ValueError, match='jewelry review'):
        apply_reviews([], review, ROOT)


def test_atma_contract_preserves_trigger_and_poison_and_audits_undated_cache():
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import build_review
    from pricing.knowledge.assessment.maintenance.inventory import ROOT

    review = build_review(ROOT, date(2026, 9, 29))
    atma = next(row for row in review['rows'] if row['name'] == "Atma's Scarab")
    assert atma['contract']['properties'] == {
        '401': 75,
        '415': 5,
        '422': 3,
        '424': 20,
        '543': 5,
        '589': 40,
    }
    assert atma['cached_observations'] > 0
    assert atma['disposition'] == 'evidence_unavailable'
    assert atma['price']['estimate_ist'] is None
    assert atma['price']['unavailable_reason'] == 'undated'
    assert 'pricing/raw/traderie/atmas-scarab.json' in review['inputs']


@pytest.mark.parametrize('field', ['fixed_triggers', 'fixed_poison_effect'])
def test_atma_special_effect_definition_changes_invalidate_review(monkeypatch, field):
    from types import SimpleNamespace

    from pricing.knowledge.assessment.maintenance import fixed_jewelry_market_review as review

    definition = dict(review.catalog().named['unique', "Atma's Scarab"])
    definition[field] = None
    monkeypatch.setattr(review, 'catalog', lambda: SimpleNamespace(named={('unique', "Atma's Scarab"): definition}))
    with pytest.raises(ValueError, match='definition changed'):
        review.template_contract("Atma's Scarab")
