"""A variable amulet's eleven resistance rolls must never share a price cohort."""

from datetime import date

import pytest


def test_mara_audit_enumerates_every_legal_resistance_roll():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit

    rows = audit([], date(2026, 9, 29))
    assert [r['all_resistance'] for r in rows] == list(range(20, 31))
    assert all(r['price']['estimate_ist'] is None for r in rows)
    assert len({tuple(sorted(r['contract']['properties'].items())) for r in rows}) == 11


@pytest.mark.parametrize('roll', [19, 31, True, 20.5])
def test_mara_contract_rejects_impossible_or_noninteger_rolls(roll):
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import template_contract

    with pytest.raises(ValueError, match='resistance roll'):
        template_contract(roll)


def test_perfect_listings_cannot_price_lower_or_inconsistent_resistance_rolls():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit

    observations = [
        {
            'name': "Mara's Kaleidoscope",
            'rarity': 'unique',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'base_code': 'amu',
            'properties': {'427': 30, '428': 30, '426': 30, '401': 30},
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'seller_id': str(i),
            'listing_id': str(i),
            'unit_policy': 'single_item',
            'ask_ist': 8 + i,
            'observed_at': '2026-09-29',
        }
        for i in range(3)
    ]
    # One mismatched resistance, absent resistance, or ladder scope cannot be
    # repaired by borrowing the other three resistances or another seller.
    observations += [
        {
            **observations[0],
            'seller_id': 'bad',
            'listing_id': 'bad',
            'properties': {'427': 30, '428': 30, '426': 30, '401': 20},
        },
        {
            **observations[0],
            'seller_id': 'missing',
            'listing_id': 'missing',
            'properties': {'427': 30, '428': 30, '426': 30},
        },
        {**observations[0], 'seller_id': 'ladder', 'listing_id': 'ladder', 'scope_status': 'rejected'},
    ]
    rows = audit(observations, date(2026, 9, 29))
    assert rows[-1]['price']['estimate_ist'] == 9
    assert rows[-1]['price']['sellers'] == 3
    assert all(r['price']['estimate_ist'] is None for r in rows[:-1])
    assert all(not r['accepted_observations'] for r in rows[:-1])


def test_mara_review_requires_all_rolls_before_closing_exact_identity():
    from copy import deepcopy

    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import apply_reviews, build_review

    review = build_review(ROOT, date(2026, 9, 29))
    row = {
        'kind': 'identity',
        'name': "Mara's Kaleidoscope",
        'category': 'unique',
        'catalog_ids': ['unique272'],
        'dimensions': {'discovery': {'state': 'reviewed'}, 'market': {'state': 'pending'}},
    }
    wrong = {**deepcopy(row), 'catalog_ids': ['unique122']}
    apply_reviews([row, wrong], review, ROOT)
    assert row['dimensions']['market']['state'] == 'reviewed'
    assert row['dimensions']['market']['disposition'] == 'reviewed_roll_partition'
    assert wrong['dimensions']['market']['state'] == 'pending'
    for mutation in ('missing-roll', 'price', 'pin'):
        changed = deepcopy(review)
        if mutation == 'missing-roll':
            changed['rows'].pop(0)
        elif mutation == 'price':
            changed['rows'][0]['price']['estimate_ist'] = 100
        else:
            changed['inputs'].pop(next(iter(changed['inputs'])))
        with pytest.raises(ValueError, match='Variable jewelry market review'):
            apply_reviews([], changed, ROOT)


def test_dwarf_star_reviews_all_four_magic_damage_reduction_rolls():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit, template_contract

    rows = audit([], date(2026, 9, 29), name='Dwarf Star')
    assert [r['magic_damage_reduction'] for r in rows] == [12, 13, 14, 15]
    assert all(r['contract']['name'] == 'Dwarf Star' for r in rows)
    assert all(r['price']['estimate_ist'] is None for r in rows)
    assert len({tuple(sorted(r['contract']['properties'].items())) for r in rows}) == 4
    for roll in (11, 16, True, 12.5):
        with pytest.raises(ValueError, match='roll'):
            template_contract(roll, name='Dwarf Star')


def test_dwarf_star_perfect_roll_asks_do_not_price_lower_rolls():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit

    observations = [
        {
            'name': 'Dwarf Star',
            'rarity': 'unique',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'base_code': 'rin',
            'properties': {'414': 15},
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'seller_id': str(i),
            'listing_id': str(i),
            'unit_policy': 'single_item',
            'ask_ist': 1,
            'observed_at': '2026-09-29',
        }
        for i in range(3)
    ]
    rows = audit(observations, date(2026, 9, 29), name='Dwarf Star')
    assert rows[-1]['price']['estimate_ist'] == 1
    assert all(r['price']['estimate_ist'] is None for r in rows[:-1])
    # Fire absorb is fixed and distinct from the variable flat MDR property.
    wrong = [{**r, 'properties': {'1867': 15}} for r in observations]
    assert all(r['price']['estimate_ist'] is None for r in audit(wrong, date(2026, 9, 29), name='Dwarf Star'))


def test_dwarf_star_market_disposition_requires_its_exact_native_identity():
    from copy import deepcopy

    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import apply_reviews, build_review

    review = build_review(ROOT, date(2026, 9, 29))
    row = {
        'kind': 'identity',
        'name': 'Dwarf Star',
        'category': 'unique',
        'catalog_ids': ['unique274'],
        'dimensions': {'discovery': {'state': 'reviewed'}, 'market': {'state': 'pending'}},
    }
    role = {**deepcopy(row), 'kind': 'role'}
    wrong = {**deepcopy(row), 'catalog_ids': ['unique272']}
    apply_reviews([row, role, wrong], review, ROOT)
    assert row['dimensions']['market']['state'] == 'reviewed'
    assert role['dimensions']['market']['state'] == 'pending'
    assert wrong['dimensions']['market']['state'] == 'pending'
    review['rows'] = [r for r in review['rows'] if r.get('magic_damage_reduction') != 12]
    with pytest.raises(ValueError, match='market review'):
        apply_reviews([], review, ROOT)


def test_nagelring_enumerates_independent_attack_rating_and_magic_find_rolls():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit, template_contract

    rows = audit([], date(2026, 9, 29), name='Nagelring')
    assert len(rows) == 26 * 16
    assert {(r['attack_rating'], r['magic_find']) for r in rows} == {
        (ar, mf) for ar in range(50, 76) for mf in range(15, 31)
    }
    assert all(r['price']['estimate_ist'] is None for r in rows)
    for roll in (75, (49, 30), (75, 31), (True, 30), (75, 30, 3)):
        with pytest.raises(ValueError, match='roll'):
            template_contract(roll, name='Nagelring')


def test_nagelring_requires_both_rolls_for_the_same_seller_cohort():
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import audit

    observations = [
        {
            'name': 'Nagelring',
            'rarity': 'unique',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'base_code': 'rin',
            'properties': {'423': 75, '461': 30},
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'seller_id': str(i),
            'listing_id': str(i),
            'unit_policy': 'single_item',
            'ask_ist': 2,
            'observed_at': '2026-09-29',
        }
        for i in range(3)
    ]
    rows = audit(observations, date(2026, 9, 29), name='Nagelring')
    priced = [r for r in rows if r['price']['estimate_ist'] is not None]
    assert [(r['attack_rating'], r['magic_find'], r['price']['estimate_ist']) for r in priced] == [(75, 30, 2)]
    for missing in ('423', '461'):
        incomplete = [
            {**r, 'properties': {k: v for k, v in r['properties'].items() if k != missing}} for r in observations
        ]
        assert all(r['price']['estimate_ist'] is None for r in audit(incomplete, date(2026, 9, 29), name='Nagelring'))


def test_nagelring_identity_needs_every_combination_not_just_boundaries():
    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.variable_jewelry_market_review import apply_reviews, build_review

    review = build_review(ROOT, date(2026, 9, 29))
    row = {
        'kind': 'identity',
        'name': 'Nagelring',
        'category': 'unique',
        'catalog_ids': ['unique120'],
        'dimensions': {'discovery': {'state': 'reviewed'}, 'market': {'state': 'pending'}},
    }
    apply_reviews([row], review, ROOT)
    assert row['dimensions']['market']['state'] == 'reviewed'
    review['rows'] = [r for r in review['rows'] if (r.get('attack_rating'), r.get('magic_find')) != (63, 22)]
    with pytest.raises(ValueError, match='missing roll outcomes'):
        apply_reviews([], review, ROOT)
