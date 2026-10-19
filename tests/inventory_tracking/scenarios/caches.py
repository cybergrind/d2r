"""The plays a test module keeps (`functools.cache` on its module level) are forgotten when the module is done.

A play is kept so that the tests reading it share one; kept for the whole session the arena's plays held the run at
1.93 GB (rca/2026-10-19/cleanup/tests.md P9). The caches of a test module serve that module's tests only: a cache
that another module reads (battle/test_tower_cellar5.py `said`, which golden/test_replay_log.py reads) lives in a
directory without the fixture."""

from types import ModuleType

import pytest


def clear_module_caches(module: ModuleType) -> None:
    """Empty every cache defined in `module` itself (not those it imported)."""
    for value in vars(module).values():
        if getattr(value, '__module__', None) == module.__name__ and callable(getattr(value, 'cache_clear', None)):
            value.cache_clear()


@pytest.fixture(autouse=True, scope='module')
def plays_forgotten_after_the_module(request: pytest.FixtureRequest):
    """For a conftest.py to take up: the module's caches emptied after its last test."""
    yield
    clear_module_caches(request.module)
