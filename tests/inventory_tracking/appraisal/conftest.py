import pytest


@pytest.fixture(autouse=True)
def no_real_compositor_config(tmp_path, monkeypatch):
    """`serve` installs hotkeys into niri's config (input/compositor.py); tests must not reach the user's."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg-config'))
