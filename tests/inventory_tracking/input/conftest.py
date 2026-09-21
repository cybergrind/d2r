import pytest


@pytest.fixture(autouse=True)
def game_identity(monkeypatch):
    """Facade tests use scripted process ownership; focus tests check actual identity validation."""
    monkeypatch.setattr('inventory_tracking.input.facade.owns_process', lambda pid, session: pid == session.process_id)
