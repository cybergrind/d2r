from datetime import date

from inventory_tracking.appraisal.sections import price_lines
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from tests.pricing.knowledge.assessment.test_comparables import contract, listing


def test_thin_exact_asks_are_dated_and_one_per_seller_without_an_estimate():
    rows = [
        listing('a', ask_ist=5),
        listing('a', listing_id='a-cheap', ask_ist=2),
        listing('b', ask_ist=3),
        listing('old', observed_at='2026-08-01'),
        listing('different', ethereal=True),
    ]
    price = price_from_comparables(evaluate(contract(), rows), today=date(2026, 9, 24))
    assert price['estimate_ist'] is None
    assert [(r['seller_id'], r['ask_ist']) for r in price['comparable_asks']] == [('a', 2), ('b', 3)]
    assert price['comparable_asks'][0]['listing_id'] == 'a-cheap'
    text = '\n'.join(price_lines({'price_estimate': price}))
    assert '2 Ist' in text
    assert '3 Ist' in text
    assert '2026-09-24' in text
    assert 'SC/NL/PC/RotW' in text
    assert 'not an estimate' in text
    assert 'Price: ~' not in text


def test_unclassified_stale_or_unmatched_rows_do_not_become_visible_thin_asks():
    for compared in (
        evaluate(None, [listing()]),
        evaluate(contract(), [listing(observed_at='2026-08-01')]),
        evaluate(contract(), [listing(ethereal=True)]),
    ):
        price = price_from_comparables(compared, today=date(2026, 9, 24))
        assert not price.get('comparable_asks')
        assert 'Comparable asks' not in '\n'.join(price_lines({'price_estimate': price}))
