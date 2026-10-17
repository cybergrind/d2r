import pytest

from inventory_tracking.macros import pickup, repair, shop, teleport, view


@pytest.fixture(autouse=True)
def no_door_entries_remembered(monkeypatch):
    """Door entries live in memory only under test: never the runs directory's file."""
    monkeypatch.setattr(teleport, 'ENTRIES', teleport.Entries(None))
    monkeypatch.setattr(teleport, 'AIMS', teleport.Entries(None))


@pytest.fixture(autouse=True)
def no_hop_landed_yet(monkeypatch):
    """The game the last hop landed in and the targets the far way failed for are kept per process:
    none carried from test to test."""
    monkeypatch.setattr(teleport, 'LANDED', [])
    monkeypatch.setattr(teleport, 'LANDING', [])
    monkeypatch.setattr(teleport, 'FAR_FAILED', {})


@pytest.fixture(autouse=True)
def no_drop_left_alone(monkeypatch):
    """The drops the pickup step leaves alone for a while are kept per process: none from test to test."""
    monkeypatch.setattr(pickup, 'SHUNNED', {})


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


@pytest.fixture(autouse=True)
def no_vendor_lifts_kept(monkeypatch, tmp_path):
    """The vendors' learned menu lifts live under the test's own directory, and no menu is pictured (no `grim`)."""
    monkeypatch.setattr(shop, 'LIFTS_FILE', tmp_path / 'menu-lifts.json')
    monkeypatch.setattr(shop, '_picture', lambda run: None)
    monkeypatch.setattr(repair, 'QUOTE_FILE', tmp_path / 'repair-quote.txt')
    monkeypatch.setattr(repair, 'QUOTED', [])
