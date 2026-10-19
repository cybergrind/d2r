from pathlib import Path

import pytest

from inventory_tracking.game import view
from inventory_tracking.macros import teleport


HERE = Path(__file__).parent
# The full arena plays (≈430 tests, ≈440 s of the ≈620 s full run; rca/2026-10-19/cleanup/tests.md P3). A routine run
# skips them (`-m "not slow"`); the full run (no `-m`) runs them, before a commit and after a change to combat, hunt
# or pursuit. The goldens and battle replays stay in the fast lane: a changed decision fails at once.
SLOW = tuple(
    HERE / path
    for path in (
        'arena/situations',
        'arena/evidence',
        'arena/test_replay.py',
        'arena/test_incident_kp4.py',
        'arena/test_scenes_threat.py',
        'stance/test_moments.py',
        'stance/test_open_field.py',
        'stance/test_export_viz.py',
        'stance/test_revivers.py',
        'explore',
        'loop/test_tick_cost.py',
        'revivers/test_scenarios.py',
    )
)


def pytest_collection_modifyitems(items):
    for item in items:
        if any(item.path == path or path in item.path.parents for path in SLOW):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def no_hop_landed_yet(monkeypatch):
    """The game the last hop landed in and the targets the far way failed for are kept per process:
    none carried from test to test."""
    monkeypatch.setattr(teleport, 'LANDED', [])
    monkeypatch.setattr(teleport, 'LANDING', [])
    monkeypatch.setattr(teleport, 'FAR_FAILED', {})


@pytest.fixture(autouse=True)
def no_corners(monkeypatch):
    """Aims beside the skill bar are off under test, as before 2026-10-11, until a run in the game has
    shown the game takes them: the routes pinned here are the ones the plain view gives. The tests of
    the corners themselves turn them on (`corners`)."""
    monkeypatch.setattr(view, 'CORNERS', [False])
    teleport.way_for.cache_clear()
    yield
    teleport.way_for.cache_clear()


@pytest.fixture
def corners(no_corners):
    view.CORNERS[0] = True
    teleport.way_for.cache_clear()
