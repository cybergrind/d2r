import importlib
import json
import sys
import types

from tests.pricing.scope_cases import VERIFIED, listings


def test_ladder_input_keeps_exactly_the_kb_scope(tmp_path, monkeypatch):
    # The solver's numpy is not a project dependency; load() does not use it.
    monkeypatch.setitem(sys.modules, 'numpy', sys.modules.get('numpy') or types.ModuleType('numpy'))
    monkeypatch.delitem(sys.modules, 'pricing.tools.rune_ladder', raising=False)
    rune_ladder = importlib.import_module('pricing.tools.rune_ladder')
    raw = tmp_path / 'pricing/raw/traderie'
    raw.mkdir(parents=True)
    for rune in rune_ladder.RUNES:
        (raw / f'rune-{rune}.json').write_text('[]')
    (raw / 'rune-Gul.json').write_text(json.dumps(listings()))
    monkeypatch.chdir(tmp_path)
    assert [row['id'] for row in rune_ladder.load()['Gul']] == VERIFIED
