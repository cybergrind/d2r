"""CLI compatibility and bundled data must survive package relocation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    'module',
    [
        'inventory_tracking',
        'inventory_tracking.appraisal_service',
        'inventory_tracking.hover_ui_probe',
        'inventory_tracking.hover_probe',
        'inventory_tracking.buff_probe',
        'inventory_tracking.build_item_metadata',
        'inventory_tracking.appraisal',
        'inventory_tracking.probes.hover_ui',
        'inventory_tracking.items.build_metadata',
    ],
)
def test_cli_help_from_outside_repository_does_not_require_game(module, tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', module, '--help'],
        cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': str(ROOT)},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert 'usage:' in result.stdout


def test_bundled_item_metadata_loads_without_repository_cwd(monkeypatch, tmp_path):
    from inventory_tracking.items.metadata import item_base, metadata

    monkeypatch.chdir(tmp_path)
    metadata.cache_clear()
    assert item_base(537)['name'] == 'Ring'
