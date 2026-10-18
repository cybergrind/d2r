"""`make serve` puts its hotkeys into niri's config and takes them out again."""

import shutil
import subprocess

import pytest

from inventory_tracking import request
from inventory_tracking.appraisal import service
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


def test_the_teleport_key_is_sent_by_the_compiled_sender_and_the_others_are_not():
    # user, 2026-10-12: only the teleport key moves to the new mechanism for now.
    text = compositor.binds_text('/venv/python', '/repo/request.py', '/run/d2r-send', '/run/service.sock')
    assert '    KP_Left repeat=false { spawn "/run/d2r-send" "teleport " "/run/service.sock"; }\n' in text
    assert text.count('/run/d2r-send') == 1
    assert text.count('/repo/request.py') == len(compositor.BINDS) - 1


@pytest.mark.skipif(shutil.which('cc') is None, reason='no C compiler')
def test_the_compiled_sender_speaks_the_services_dialect(tmp_path):
    import socket
    import time

    binary = compositor.build_sender(tmp_path)
    assert binary is not None
    endpoint = tmp_path / 'service.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(2)
        before = time.monotonic()
        assert subprocess.run([binary, 'teleport ', str(endpoint)], timeout=5, check=False).returncode == 0
        data = server.recv(256)
    asked = []

    class Macro:
        def request(self, *args, **notes):
            asked.append((args, notes))
            return True

    assert service.for_macro(data)
    assert service.dispatch(data, time.monotonic(), None, None, macro=Macro())
    ((stamp, _now, routine), notes) = asked[0]
    assert routine == 'teleport'
    assert before <= stamp <= time.monotonic()
    assert 0 <= notes['spawn_ms'] < 1000
    assert 0 <= notes['spawn_cpu_ms'] < 1000
    assert subprocess.run([binary, 'teleport ', str(tmp_path / 'none.sock')], timeout=5, check=False).returncode == 1


def test_tz_key_is_available_only_for_an_explicit_future_install():
    assert 'KP_Home' not in compositor.binds_text()
    assert '"tz-loop"' in compositor.binds_text(tz_loop=True)


def test_without_a_compiler_the_binds_keep_the_script(monkeypatch, tmp_path):
    def missing(*args, **kwargs):
        raise FileNotFoundError('cc')

    monkeypatch.setattr(compositor.subprocess, 'run', missing)
    assert compositor.build_sender(tmp_path) is None
    assert 'd2r-send' not in compositor.binds_text(compiled=compositor.build_sender(tmp_path))
