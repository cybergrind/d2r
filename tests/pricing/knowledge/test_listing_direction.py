import pytest

from pricing.knowledge.market import summarize
from tests.pricing.knowledge.test_market import listing, norm


@pytest.mark.parametrize(
    ('changes', 'kind'),
    [
        ({'selling': False}, 'buy_offer'),
        ({'active': False}, 'inactive_listing'),
        ({'completed': True}, 'inactive_listing'),
    ],
)
def test_non_seller_asks_cannot_enter_price_summary(changes, kind):
    row = norm(listing(active=True, selling=True, completed=False))
    raw = listing(active=True, selling=True, completed=False)
    raw.update(changes)
    excluded = norm(raw)
    assert excluded['evidence_kind'] == kind
    assert summarize([excluded])['priced_sellers'] == 0
    assert summarize([row])['priced_sellers'] == 1
