"""`make serve` puts its hotkeys into niri's config and takes them out again."""

import shutil
import subprocess

import pytest

from inventory_tracking import request
from inventory_tracking.input import compositor


@pytest.fixture
def config(tmp_path):
    path = tmp_path / 'niri' / 'config.kdl'
    path.parent.mkdir()
    path.write_text('binds {\n    Mod+C { center-column; }\n}')
    return path


def test_every_bind_sends_a_kind_the_sender_knows():
    assert set(compositor.BINDS.values()) <= set(request.PREFIXES)
    text = compositor.binds_text('/venv/python', '/repo/request.py')
    assert '    Alt+D repeat=false { spawn "/venv/python" "-S" "/repo/request.py" "appraise"; }\n' in text
    assert text.count('spawn') == len(compositor.BINDS)


def test_the_binds_live_only_inside_the_block(config, monkeypatch):
    monkeypatch.setattr(compositor, 'invalid', lambda path: None)
    target = config.with_name(compositor.HOTKEYS_FILE)
    with compositor.hotkeys(config) as bound:
        assert bound
        assert 'KP_Left' in target.read_text()
        assert config.read_text().endswith(f'{compositor.INCLUDE}\n')
    assert 'binds' not in target.read_text()
    assert target.exists()  # the include line stays, so the file does


def test_a_restored_config_gets_its_include_back_once(config, monkeypatch):
    monkeypatch.setattr(compositor, 'invalid', lambda path: None)
    original = config.read_text()
    for _ in range(2):
        with compositor.hotkeys(config):
            pass
    assert config.read_text().count(compositor.HOTKEYS_FILE) == 1
    config.write_text(original)  # what happened on 2026-10-10
    with compositor.hotkeys(config):
        assert compositor.INCLUDE in config.read_text()
        assert config.read_text().startswith(original)


def test_a_commented_out_include_does_not_count(config):
    config.write_text(f'// {compositor.INCLUDE}\n')
    assert compositor.ensure_include(config)


def test_a_config_niri_rejects_keeps_no_binds(config, monkeypatch, caplog):
    monkeypatch.setattr(compositor, 'invalid', lambda path: 'duplicate keybind')
    with compositor.hotkeys(config) as bound:
        assert not bound
        assert 'binds' not in config.with_name(compositor.HOTKEYS_FILE).read_text()
    assert 'duplicate keybind' in caplog.text


def test_without_a_niri_config_nothing_is_written(tmp_path):
    with compositor.hotkeys(tmp_path / 'niri' / 'config.kdl') as bound:
        assert not bound
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(shutil.which('niri') is None, reason='niri is not installed')
def test_niri_accepts_the_generated_config(config):
    with compositor.hotkeys(config) as bound:
        assert bound
        done = subprocess.run(['niri', 'validate', '-c', str(config)], capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr
