import pytest

from inventory_tracking.game import view
from inventory_tracking.macros import pickup, repair, runner, shop, stash, teleport


@pytest.fixture(autouse=True)
def no_card_wait(monkeypatch):
    """A run's card stays 4 s after it ends (runner.py CARD_SECONDS): not under test. A test of the card's own
    lifetime sets it back."""
    monkeypatch.setattr(runner, 'CARD_SECONDS', 0)


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
    monkeypatch.setattr(teleport, 'MISSED', [])
    monkeypatch.setattr(teleport, 'FAR_FAILED', {})


@pytest.fixture(autouse=True)
def zone_navigation_off(monkeypatch):
    """Zone navigation (zonenav.ACTS, zonenav.ROTATION) is the live loop's choice of acts and of the rotating zones: off
    under test, so the itinerary's tests keep their trips; a zone test turns it on for its acts or the rotation."""
    from inventory_tracking.macros import zonenav

    monkeypatch.setattr(zonenav, 'ACTS', frozenset())
    monkeypatch.setattr(zonenav, 'ROTATION', False)


@pytest.fixture(autouse=True)
def no_town_drops_counted(monkeypatch):
    """The items put down in town in the game (visit.py `_down`) are kept per process: none from test to test."""
    from inventory_tracking.macros import visit

    monkeypatch.setattr(visit, '_down', {'game': '', 'items': 0})


@pytest.fixture(autouse=True)
def no_drop_left_alone(monkeypatch):
    """The drops the pickup step leaves alone for a while, and the aims looked at for them, are kept per process: none
    from test to test."""
    monkeypatch.setattr(pickup, 'SHUNNED', {})
    monkeypatch.setattr(pickup, 'LOOKED', {})


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


@pytest.fixture(autouse=True)
def no_deposit_refused(monkeypatch):
    """A refused deposit ends the deposits per process (stash.py REFUSED): none from test to test, no picture."""
    monkeypatch.setattr(stash, 'REFUSED', [])
    monkeypatch.setattr(stash, '_picture', lambda what: None)
