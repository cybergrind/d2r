import pytest

from inventory_tracking.macros import teleport


@pytest.fixture(autouse=True)
def no_door_entries_remembered(monkeypatch):
    """Door entries live in memory only under test: never the runs directory's file."""
    monkeypatch.setattr(teleport, 'ENTRIES', teleport.Entries(None))
    monkeypatch.setattr(teleport, 'AIMS', teleport.Entries(None))
