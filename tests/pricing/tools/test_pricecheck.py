from pathlib import Path

import pytest

from tests.pricing.scope_cases import VERIFIED, listings


if not (Path(__file__).resolve().parents[3] / 'pricing/data/wp-f-ladder.json').exists():
    pytest.skip('pricecheck reads the local, git-ignored rune ladder at import', allow_module_level=True)

from pricing.tools import pricecheck


def test_band_keeps_exactly_the_kb_scope():
    scoped, offer_only, values, _, unconverted = pricecheck.band(listings())
    assert [listing['id'] for listing in scoped] == VERIFIED
    assert (offer_only, unconverted) == (0, {})
    assert len(values) == len(VERIFIED)
