"""Pricing review must distinguish missing evidence from unfinished comparison code."""

from copy import deepcopy
from datetime import date

import pytest

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.material_market_review import (
    apply_material_market_reviews,
    audit_materials,
    build_review,
)
from tests.pricing.knowledge.assessment.test_socket_material_prices import observation


DAY = date(2026, 9, 28)


def test_audit_prices_fixed_materials_only_from_exact_dated_independent_single_units():
    rows = [observation('Ist Rune', str(i)) for i in range(3)]
    rows += [observation('Ist Rune', 'bulk', amount=10), observation('Ist Rune', 'bad', extra=[('738', 'bool', True)])]
    result = audit_materials(rows, DAY)
    item = next(r for r in result if r['name'] == 'Ist Rune')
    assert item['disposition'] == 'estimate'
    assert item['price']['estimate_ist'] == 1
    assert item['cached_observations'] == 5
    assert len(item['accepted_observations']) == 3
    assert sum(item['rejection_counts'].values()) >= 2
    assert len(result) == 68
    el = next(r for r in result if r['name'] == 'El Rune')
    assert el['disposition'] == 'evidence_unavailable'
    assert el['price']['unavailable_reason'] == 'no_matches'


def test_undated_matches_are_not_priced_using_listing_update_or_ladder_date():
    rows = [
        observation('Ist Rune', str(i)) | {'observed_at': None, 'listing_updated_at': DAY.isoformat()} for i in range(3)
    ]
    item = next(r for r in audit_materials(rows, DAY) if r['name'] == 'Ist Rune')
    assert item['price']['unavailable_reason'] == 'undated'
    assert item['price']['estimate_ist'] is None


def test_missing_handler_is_an_implementation_error_not_reviewed_market_absence(monkeypatch):
    from pricing.knowledge.assessment.handlers.socket_material import SocketMaterialHandler

    monkeypatch.setattr(SocketMaterialHandler, 'contract', lambda *a: (None, ['unimplemented test branch']))
    with pytest.raises(ValueError, match='comparison implementation'):
        audit_materials([], DAY)


@pytest.fixture(scope='module')
def reviewed():
    return build_review(ROOT, DAY)


def identity(**changes):
    row = {
        'id': 'identity:el',
        'kind': 'identity',
        'name': 'El Rune',
        'category': 'misc',
        'catalog_ids': ['r01'],
        'dimensions': {
            'discovery': {'state': 'reviewed'},
            'market': {'state': 'pending'},
            'desirability': {'state': 'pending'},
        },
    }
    row.update(changes)
    return row


def test_exact_native_identity_inherits_only_market_review(reviewed):
    rows = [
        identity(),
        identity(id='use:el', kind='use_quality'),
        identity(id='ambiguous', catalog_ids=['r01', 'r02']),
        identity(id='wrong-name', name='Eld Rune'),
    ]
    apply_material_market_reviews(rows, reviewed, ROOT)
    assert rows[0]['dimensions']['market']['state'] == 'reviewed'
    assert rows[0]['dimensions']['market']['unit_quantity'] == 1
    assert rows[0]['dimensions']['desirability']['state'] == 'pending'
    assert all(r['dimensions']['market']['state'] == 'pending' for r in rows[1:])


@pytest.mark.parametrize('tamper', ['omit_identity', 'forge_price', 'stale_input', 'stale_raw'])
def test_incomplete_or_forged_review_cannot_close_the_ledger(reviewed, tamper):
    review = deepcopy(reviewed)
    if tamper == 'omit_identity':
        review['rows'].pop()
    elif tamper == 'forge_price':
        review['rows'][0]['price']['estimate_ist'] = 500
    elif tamper == 'stale_raw':
        raw = next(path for path in review['inputs'] if path.startswith('pricing/raw/'))
        review['inputs'][raw] = '0' * 64
    else:
        review['inputs']['pricing/data/appraisal-market.jsonl'] = '0' * 64
    with pytest.raises(ValueError, match=r'[Mm]aterial pricing review'):
        apply_material_market_reviews([identity()], review, ROOT)


def test_absent_review_keeps_market_pending():
    rows = [identity()]
    apply_material_market_reviews(rows, None, ROOT)
    assert rows[0]['dimensions']['market']['state'] == 'pending'


def test_matrix_links_native_material_without_closing_other_dimensions(reviewed):
    from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
    from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs

    args = inputs()
    args[0]['identities'][0].update(name='El Rune', category='misc', catalog_ids=['r01'])
    result = build_matrix(*args, material_market_reviews=reviewed)
    row = next(r for r in result['rows'] if r['id'] == 'identity:u')
    assert row['dimensions']['market']['state'] == 'reviewed'
    assert row['dimensions']['report']['state'] == 'pending'
    assert row['dimensions']['desirability']['state'] == 'pending'


def test_completion_verifies_review_input_pins(reviewed):
    from pricing.knowledge.assessment.maintenance.completion import verify_artifact_inputs

    verify_artifact_inputs({'material_market_reviews': reviewed}, ROOT)
    changed = deepcopy(reviewed)
    changed['inputs']['pricing/data/appraisal-market.jsonl'] = '0' * 64
    with pytest.raises(ValueError, match='Stale completion input'):
        verify_artifact_inputs({'material_market_reviews': changed}, ROOT)
