import json

import pytest

from pricing.tools import traderie
from tests.pricing.scope_cases import VERIFIED, listings


def pages(first):
    """A fake Traderie API: `first` on page 0, nothing after; the Ist catalog item for `runes`."""

    def get(url):
        if '/items?' in url:
            return {'items': [{'id': 'ist', 'type': 'runes', 'name': 'Ist Rune'}]}
        return {'listings': first if 'page=0' in url else []}

    return get


@pytest.mark.parametrize('flags', [['--scope'], ['--sc', '--nl', '--pc'], ['--sc']])
def test_listings_scope_flags_keep_exactly_the_kb_scope(flags, monkeypatch, capsys):
    monkeypatch.setattr(traderie, 'get', pages(listings()))
    traderie.main(['listings', 'id', '1', *flags, '--json'])
    assert [row['id'] for row in json.loads(capsys.readouterr().out)] == VERIFIED


def test_listings_without_a_scope_flag_keep_everything(monkeypatch, capsys):
    monkeypatch.setattr(traderie, 'get', pages(listings()))
    traderie.main(['listings', 'id', '1', '--json'])
    assert len(json.loads(capsys.readouterr().out)) == len(listings())


def test_rune_asks_keep_exactly_the_kb_scope(monkeypatch, capsys):
    rows = listings()
    for row in rows:
        row['prices'] = [{'name': 'Gul Rune', 'quantity': 1, 'group': 0, 'type': 'runes'}]
    monkeypatch.setattr(traderie, 'get', pages(rows))
    traderie.main(['runes', 'Ist'])
    assert capsys.readouterr().out.count('stack ask: 1x Gul Rune') == len(VERIFIED)
