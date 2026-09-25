from copy import deepcopy
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from tests.pricing.knowledge.assessment.test_comparables import contract, listing


@pytest.mark.parametrize('observed', [None, 'invalid', '2026-08-24', '2026-09-25'])
def test_historical_or_invalid_dates_do_not_poison_sufficient_fresh_evidence(observed):
    rows = [listing(str(i), ask_ist=i) for i in (1, 2, 3)]
    rows.append(listing('historical', observed_at=observed, ask_ist=1000))
    compared = evaluate(contract(), rows)
    before = deepcopy(compared)
    price = price_from_comparables(compared, today=date(2026, 9, 24))
    assert price['estimate_ist'] == 2
    assert price['sellers'] == 3
    assert price['high_ist'] == 3
    assert price['dates'] == ['2026-09-24']
    assert sum(price['excluded_observations'].values()) == 1
    assert compared == before


def test_only_fresh_sellers_count_toward_publication_and_dispersion_still_applies():
    rows = [listing(str(i), ask_ist=i) for i in (1, 2)]
    rows.append(listing('old', observed_at='2026-08-24', ask_ist=2))
    price = price_from_comparables(evaluate(contract(), rows), today=date(2026, 9, 24))
    assert price['estimate_ist'] is None
    assert price['sellers'] == 2
    assert price['excluded_observations'] == {'stale': 1}
    rows.append(listing('fresh-expensive', ask_ist=100))
    price = price_from_comparables(evaluate(contract(), rows), today=date(2026, 9, 24))
    assert price['estimate_ist'] is None
    assert price['unavailable_reason'] == 'dispersed'
