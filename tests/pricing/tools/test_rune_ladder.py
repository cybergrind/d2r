import json

import pytest

from pricing.tools import rune_ladder
from tests.pricing.scope_cases import VERIFIED, listings


def test_lstsq_solves_an_overdetermined_system():
    # x0 + x1 = 3, x0 - x1 = 1, 2 x0 = 4.2: the normal equations 6 x0 = 12.4, 2 x1 = 2.
    assert rune_ladder.lstsq([[1, 1], [1, -1], [2, 0]], [3, 1, 4.2]) == pytest.approx([12.4 / 6, 1.0])


def test_lstsq_keeps_an_unknown_no_row_names_at_zero():
    assert rune_ladder.lstsq([[1, 0], [2, 0]], [1, 2]) == pytest.approx([1.0, 0.0])


def test_ladder_input_keeps_exactly_the_kb_scope(tmp_path, monkeypatch):
    raw = tmp_path / 'pricing/raw/traderie'
    raw.mkdir(parents=True)
    for rune in rune_ladder.RUNES:
        (raw / f'rune-{rune}.json').write_text('[]')
    (raw / 'rune-Gul.json').write_text(json.dumps(listings()))
    monkeypatch.chdir(tmp_path)
    assert [row['id'] for row in rune_ladder.load()['Gul']] == VERIFIED
