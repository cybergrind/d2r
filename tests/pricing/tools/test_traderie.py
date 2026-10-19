import json

import pytest

from pricing.knowledge import refresh
from pricing.tools import traderie
from tests.pricing.scope_cases import ROTW, VERIFIED, changed, listings, raw_properties


API = 'https://traderie.com/api/diablo2resurrected'


def test_the_tools_use_the_one_refresh_client():
    assert traderie.fetch_json is refresh.fetch_json
    assert traderie.API == refresh.API == API


def test_request_urls():
    assert traderie.listings_url('123', 0) == f'{API}/listings?item=123&page=0'
    assert traderie.listings_url('123', 2, sockets_min='4') == f'{API}/listings?item=123&page=2&prop_402Min=4'
    assert traderie.search_url('Ist rune') == f'{API}/items?search=Ist%20rune'
    assert traderie.catalog_url('base', 3) == f'{API}/items?type=base&page=3'


def test_get_answers_the_clients_json(monkeypatch):
    monkeypatch.setattr(refresh, '_fetch_response', lambda url: ('{"items": []}', '200', {}))
    assert traderie.get(traderie.search_url('Ist')) == {'items': []}


def test_get_ends_the_tool_on_a_rate_limit(monkeypatch):
    monkeypatch.setattr(refresh, '_fetch_response', lambda url: ('slow down', '429', {'retry-after': '60'}))
    with pytest.raises(SystemExit, match='HTTP 429; Retry-After: 60'):
        traderie.get(traderie.search_url('Ist'))


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


def test_listings_request_each_page_with_the_socket_filter_until_one_is_empty(monkeypatch, capsys):
    answer, urls = pages(listings()), []
    monkeypatch.setattr(traderie, 'get', lambda url: urls.append(url) or answer(url))
    traderie.main(['listings', 'id', '3', '--sockets-min', '4', '--json'])
    assert urls == [traderie.listings_url('id', 0, '4'), traderie.listings_url('id', 1, '4')]


@pytest.mark.parametrize(
    'change',
    [
        {'p799': ('string', 'hardcore')},
        {'p800': ('bool', True)},
        {'p798': ('string', 'Playstation')},
        {'p1854': ('string', 'lord of destruction')},
    ],
    ids=['799-hardcore', '800-ladder', '798-console', '1854-lod'],
)
def test_scope_drops_a_listing_off_any_one_scope_property(change, monkeypatch, capsys):
    rows = [
        {'id': 'in', 'properties': raw_properties(ROTW)},
        {'id': 'out', 'properties': raw_properties(changed(**change))},
    ]
    monkeypatch.setattr(traderie, 'get', pages(rows))
    traderie.main(['listings', 'id', '1', '--scope', '--json'])
    assert [row['id'] for row in json.loads(capsys.readouterr().out)] == ['in']
