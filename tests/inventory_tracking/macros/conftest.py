import pytest

from inventory_tracking.macros import teleport, view


@pytest.fixture(autouse=True)
def no_door_entries_remembered(monkeypatch):
    """Door entries live in memory only under test: never the runs directory's file."""
    monkeypatch.setattr(teleport, 'ENTRIES', teleport.Entries(None))
    monkeypatch.setattr(teleport, 'AIMS', teleport.Entries(None))


@pytest.fixture(autouse=True)
def no_far_ways_given_up(monkeypatch):
    """The targets the far potential failed for are kept per process: none carried from test to test."""
    monkeypatch.setattr(teleport, 'FAR_FAILED', set())


@pytest.fixture(autouse=True)
def no_corners(monkeypatch):
    """Aims beside the skill bar are off under test, as before 2026-10-11, until a run in the game has
    shown the game takes them: the routes pinned here are the ones the plain view gives. The tests of
    the corners themselves turn them on (`corners`)."""
    monkeypatch.setattr(view, 'CORNERS', [False])
    monkeypatch.setattr(teleport, 'CORNERS', view.CORNERS)
    teleport.way_for.cache_clear()
    yield
    teleport.way_for.cache_clear()


@pytest.fixture
def corners(no_corners):
    view.CORNERS[0] = True
    teleport.way_for.cache_clear()
