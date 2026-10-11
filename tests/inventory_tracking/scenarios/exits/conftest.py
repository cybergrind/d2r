import pytest

from inventory_tracking.macros import teleport


@pytest.fixture(autouse=True)
def no_door_memory_on_disk(monkeypatch):
    """Door entries and aims live in memory only under test: never the runs directory's files."""
    monkeypatch.setattr(teleport, 'ENTRIES', teleport.Entries(None))
    monkeypatch.setattr(teleport, 'AIMS', teleport.Entries(None))
    teleport.way_for.cache_clear()
