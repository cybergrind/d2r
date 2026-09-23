from inventory_tracking.native import unit_probe
from inventory_tracking.probes import runtime as probe


def test_item_probe_rejects_unverified_build_before_capture(monkeypatch):
    monkeypatch.setattr(probe, 'reader_environment', dict)
    monkeypatch.setattr(probe, 'select_game_process', lambda pid: 1)
    monkeypatch.setattr(
        probe, 'inspect_game', lambda pid: {'memory_access': True, 'executable_fingerprint': {'sha256': 'wrong'}}
    )
    monkeypatch.setattr(probe, 'inspect_images', lambda *args: (_ for _ in ()).throw(AssertionError('must not scan')))
    report = {}
    probe.run_diagnostics(report, None, images=True, item_class=537)
    assert report['state'] == 'failed'
    assert 'unsupported' in str(report['error']).lower()


def test_requested_item_stats_failure_is_visible_in_probe_completion(tmp_path, monkeypatch):
    snapshot = {
        'status': 'research',
        'groups': {'players': {'complete': True, 'units': []}, 'items': {'complete': True, 'units': []}},
        'resources': {'complete': False, 'items': []},
    }
    monkeypatch.setattr(unit_probe, 'sample_units', lambda *args, **kwargs: snapshot)
    result = unit_probe.inspect_units(1, {}, {}, tmp_path, item_class=537)
    assert result['complete'] is False
