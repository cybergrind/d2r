import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.andariel_market_review import audit, intrinsic_rolls


@pytest.fixture(scope='module')
def rows():
    return [
        json.loads(line)
        for line in Path('pricing/data/appraisal-market.jsonl').read_text().splitlines()
        if json.loads(line).get('name') == "Andariel's Visage"
    ]


def test_cached_cohorts_do_not_turn_unknown_sockets_into_native_roll_proof(rows):
    result = audit(rows)
    # The shared scope validator also accepts the explicit LoD+RotW listing.
    assert result['eligible_asks'] == 39
    assert result['verified_intrinsic_rows'] == 4
    assert result['verified_intrinsic_sellers'] == 2
    assert result['complete_material_roll_rows'] == 2
    assert result['complete_material_roll_sellers'] == 1
    assert result['pricing_disposition'] == 'insufficient_variant_evidence'
    assert result['premium_threshold'] is None


@pytest.mark.parametrize('field', ['ethereal', 'socket_contents', 'sockets'])
def test_missing_variant_cannot_be_filled_from_listing_rolls(rows, field):
    row = deepcopy(rows[0])
    row[field] = None
    assert intrinsic_rolls(row) is None


@pytest.mark.parametrize('property_id', ['437', '462', '425'])
def test_boolean_and_impossible_material_rolls_are_rejected(rows, property_id):
    for value in (True, 999, -1, 3.5):
        row = deepcopy(rows[0])
        row['properties'][property_id] = value
        assert intrinsic_rolls(row) is None


def test_jewel_payload_name_does_not_prove_its_modifiers(rows):
    row = deepcopy(rows[0])
    row['properties']['934'] = 'Jewel'
    assert intrinsic_rolls(row) is None


@pytest.mark.parametrize('failure', ['ladder', 'hardcore', 'inactive', 'sold', 'buying', 'quantity', 'undated', 'nan'])
def test_market_review_excludes_incompatible_or_invalid_asks(rows, failure):
    row = deepcopy(rows[0])
    if failure == 'ladder':
        row['properties']['800'] = True
    elif failure == 'hardcore':
        row['properties']['799'] = 'hardcore'
    elif failure == 'inactive':
        row['listing_status']['active'] = False
    elif failure == 'sold':
        row['listing_status']['completed'] = True
    elif failure == 'buying':
        row['listing_status']['selling'] = False
    elif failure == 'quantity':
        row['amount'] = 2
    elif failure == 'undated':
        row.pop('observed_at')
    else:
        row['ask_ist'] = float('nan')
    assert audit([row])['eligible_asks'] == 0


def test_duplicate_rows_never_create_independent_sellers(rows):
    result = audit([rows[0]] * 3)
    assert result['eligible_asks'] == 1
    assert result['verified_intrinsic_sellers'] == 1


def test_new_seller_cohort_requires_exact_comparison_review_not_a_price(rows):
    cohort = []
    for index in range(3):
        row = deepcopy(rows[0])
        row.update(id=f'test-{index}', seller_id=f'seller-{index}')
        cohort.append(row)
    result = audit(cohort)
    assert result['pricing_disposition'] == 'requires_exact_comparison_review'
    assert result['premium_threshold'] is None


def test_conflicting_duplicate_evidence_fails_the_review(rows):
    changed = deepcopy(rows[0])
    changed['properties']['437'] = 29
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        audit([rows[0], changed])
