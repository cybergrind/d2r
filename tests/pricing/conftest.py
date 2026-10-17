"""Shared hooks for the pricing tests."""

import pytest

from tests.pricing.matchers import forget_comparisons


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """A parametrized test's matchers forget the result they were compared with (tests/pricing/matchers.py)."""
    callspec = getattr(item, 'callspec', None)
    if callspec is not None:
        forget_comparisons(callspec.params)
