"""Shared hooks for the pricing tests."""

import hashlib
import os
import pickle
from pathlib import Path

import pytest

from pricing.knowledge.assessment import build_profiles
from pricing.knowledge.assessment.maintenance import stat_configurations
from tests.pricing.matchers import forget_comparisons
from tests.pricing.session_cache import memoize


def _profiles_key(root=build_profiles.ROOT):
    """The working tree's profiles only; a test's own root or patched rules file computes afresh."""
    if Path(root).resolve() != build_profiles.ROOT.resolve():
        return None
    return str(build_profiles.RULES)


def _configurations_key(reviews, profiles, *, root=None):
    try:
        content = pickle.dumps((reviews, profiles), protocol=5)
    except TypeError, pickle.PicklingError:
        return None
    return hashlib.sha256(content).hexdigest(), None if root is None else str(Path(root).resolve())


# Installed before the test modules import them: build() took 3.5 s and the stat compiler 1.7 s per call,
# from ~340 call sites (cleanup phase 2, 2026-10-19). Compiled configurations are deeply frozen, so shared.
# D2R_PRICING_CACHE=off runs without them, to rule the caches out.
if os.environ.get('D2R_PRICING_CACHE') != 'off':
    build_profiles.build = memoize(build_profiles.build, _profiles_key)
    stat_configurations.compile_stat_configurations = memoize(
        stat_configurations.compile_stat_configurations, _configurations_key, copy=False
    )


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    """A parametrized test's matchers forget the result they were compared with (tests/pricing/matchers.py)."""
    callspec = getattr(item, 'callspec', None)
    if callspec is not None:
        forget_comparisons(callspec.params)
