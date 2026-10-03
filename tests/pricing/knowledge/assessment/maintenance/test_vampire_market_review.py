from datetime import date

import pytest

from pricing.knowledge.assessment.maintenance.vampire_market_review import audit, template_contract


def test_native_extremes_remain_distinct_comparison_variants():
    low = template_contract(6, 6, 15, 10, False)
    high = template_contract(8, 8, 20, 15, True)
    assert low['ethereal'] is False
    assert high['ethereal'] is True
    assert low['sockets'] == high['sockets'] == 0
    assert low['properties'] != high['properties']


@pytest.mark.parametrize(
    'rolls',
    [(5, 6, 15, 10, False), (6, 9, 15, 10, False), (6, 6, 21, 10, False), (6, 6, 15, 16, False), (6, 6, 15, 10, 0)],
)
def test_illegal_or_unknown_variants_are_not_market_absence(rolls):
    with pytest.raises(ValueError, match=r'Unreviewed|explicit'):
        template_contract(*rolls)


def test_missing_cache_yields_reviewed_absence_for_every_original_unsocketed_roll():
    rows = audit([], date(2026, 10, 3))
    assert len(rows) == 648
    assert len({tuple(r['variant'].values()) for r in rows}) == 648
    assert all(r['disposition'] == 'evidence_unavailable' for r in rows)
    assert all(r['price']['estimate_ist'] is None for r in rows)


def test_only_exact_variant_independent_dated_sellers_can_price():
    contract = template_contract(8, 7, 20, 14, False)
    rows = [
        {
            **contract,
            'properties': dict(contract['properties']),
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'unit_policy': 'single_item',
            'amount': 1,
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 2,
            'observed_at': '2026-10-03',
        }
        for i in range(3)
    ]
    reviewed = audit(rows, date(2026, 10, 3))
    estimates = [r for r in reviewed if r['disposition'] == 'estimate']
    assert len(estimates) == 1
    assert estimates[0]['variant'] == {
        'life_leech': 8,
        'mana_leech': 7,
        'physical_reduction': 20,
        'magic_reduction': 14,
        'ethereal': False,
    }


def test_missing_comparison_implementation_is_not_reviewed_absence(monkeypatch):
    monkeypatch.setattr(
        'pricing.knowledge.assessment.maintenance.vampire_market_review.NamedHandler.contract',
        lambda *args: (None, ['unsupported stat']),
    )
    with pytest.raises(ValueError, match='implementation incomplete'):
        audit([], date(2026, 10, 3))


def test_missing_ethereal_fact_cannot_borrow_exact_roll_price():
    contract = template_contract(8, 8, 20, 15, False)
    observations = [
        {
            **contract,
            'ethereal': None,
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'unit_policy': 'single_item',
            'amount': 1,
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': 2,
            'observed_at': '2026-10-03',
        }
        for i in range(3)
    ]
    assert all(row['disposition'] == 'evidence_unavailable' for row in audit(observations, date(2026, 10, 3)))


@pytest.mark.parametrize('defense', range(200, 315, 2))
def test_all_non_ethereal_upgrade_defense_outcomes(defense):
    contract = template_contract(8, 8, 20, 15, False, base_name='Bone Visage', defense=defense)
    assert contract['base_code'] != template_contract(8, 8, 20, 15, False)['base_code']
    assert contract['properties']['1855'] == defense


@pytest.mark.parametrize('defense', [199, 201, 251, 313, 315, 378, None])
def test_upgrade_does_not_borrow_original_max_plus_one_or_unattainable_defense(defense):
    with pytest.raises(ValueError, match='defense'):
        template_contract(8, 8, 20, 15, False, base_name='Bone Visage', defense=defense)


def test_ethereal_upgrade_requires_separate_proof():
    with pytest.raises(ValueError, match='Ethereal upgrade'):
        template_contract(8, 8, 20, 15, True, base_name='Bone Visage', defense=470)


@pytest.mark.parametrize('ethereal', [False, True])
def test_open_quest_socket_has_its_own_contract(ethereal):
    empty = template_contract(8, 8, 20, 15, ethereal, sockets=1)
    assert empty['sockets'] == 1
    assert empty['socket_contents'] == 'empty'
    assert empty != template_contract(8, 8, 20, 15, ethereal)


@pytest.mark.parametrize('sockets', [None, True, -1, 2, 3])
def test_illegal_or_unknown_quest_sockets_are_not_reviewed(sockets):
    with pytest.raises(ValueError, match='socket'):
        template_contract(8, 8, 20, 15, False, sockets=sockets)
