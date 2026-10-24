import pytest


@pytest.fixture(autouse=True)
def no_real_compositor_config(tmp_path, monkeypatch):
    """`serve` installs hotkeys into niri's config (input/compositor.py); tests must not reach the user's."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg-config'))


@pytest.fixture(autouse=True)
def no_collection(monkeypatch):
    """The Alt+D card's CARD line reads owned copies from the collection (loot/value.py `CollectionCopies`): none in
    these tests, so none reads the player's database (a set or unique is then kept, S8)."""
    from inventory_tracking.loot import assess, value

    monkeypatch.setattr(value, 'CollectionCopies', assess.NoCopies)
    monkeypatch.setattr(assess, 'SHADOW_SAID', set())
