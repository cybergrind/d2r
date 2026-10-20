import pytest

from inventory_tracking.macros import tzroutine


@pytest.fixture(autouse=True)
def no_forced_plan_kept():
    """A script forced ready (harness.py `force_ready`) plans its act only within its test: the itinerary cache is
    cleared before and after, so no other test reads a plan made by a script not ready."""
    tzroutine.itinerary.cache_clear()
    yield
    tzroutine.itinerary.cache_clear()
