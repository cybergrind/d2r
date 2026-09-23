"""Different appraisal intents must choose independent, strict facets."""

import json
import socket

import pytest

from pricing.knowledge.__main__ import main
from pricing.knowledge.index import build_index, lookup, search


@pytest.fixture
def database(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Faceted search attempted networking')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    rows = [
        {'name': 'Crystal Sword', 'kind': 'catalog'},
        {'name': 'Broad Sword', 'kind': 'catalog'},
        *[
            {
                'name': base,
                'kind': 'base_rule',
                'predicates': {'sockets': sockets, 'quality': ['normal', 'superior']},
                'details': {'runeword': word},
            }
            for base, sockets, word in [
                ('Crystal Sword', 4, 'Spirit'),
                ('Crystal Sword', 3, 'Test recipe'),
                ('Broad Sword', 4, 'Spirit'),
            ]
        ],
        *[
            {
                'name': base,
                'kind': 'market',
                'rarity': 'magic',
                'properties': props,
                'source': 'fixture',
                'seller_id': str(i),
            }
            for i, (base, props) in enumerate(
                [
                    ('Cinquedeas', {'1577': 3}),
                    ('Mithril Point', {'1577': 3}),
                    ('Cinquedeas', {'1577': 2}),
                    ('Mithril Point', {'1579': 3}),
                    ('Kris', {}),
                    ('Kris', {'1577': '3'}),
                    ('Kris', {'1577': True}),
                ]
            )
        ],
        {'name': 'Misleading skill text', 'kind': 'demand', 'details': {'reason': '+3 Sigil: Death'}},
        {
            'name': "Naj's Circlet",
            'kind': 'item_fact',
            'item_id': 'test:naj',
            'quality': 'set',
            'aliases': ['Circlet'],
            'requirements': {'level': 28},
            'stats': [],
        },
    ]
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    db = tmp_path / 'index.sqlite3'
    build_index([source], db)
    return db


def test_base_only_is_exact_not_lexical(database):
    rows = search(database, base_name='Crystal Sword', kind='catalog')
    assert [r['name'] for r in rows] == ['Crystal Sword']
    assert not search(database, base_name='Crystal')


def test_skill_only_crosses_bases_and_rejects_missing_wrong_skill_and_text(database):
    rows = search(database, properties={'1577': 3})
    assert {r['name'] for r in rows} == {'Cinquedeas', 'Mithril Point'}
    assert len(rows) == 2


def test_minimum_skill_and_base_facets_intersect_before_limit(database):
    rows = search(database, base_name='Cinquedeas', property_min={'1577': 3}, limit=1)
    assert len(rows) == 1
    assert rows[0]['properties']['1577'] == 3
    assert len(search(database, property_min={'1577': 2})) == 3
    assert not search(database, property_min={'1577': 4})


@pytest.mark.parametrize(('sockets', 'expected'), [(4, ['Spirit']), (3, ['Test recipe']), (2, [])])
def test_correct_base_and_sockets_are_both_required(database, sockets, expected):
    rows = search(database, base_name='Crystal Sword', kind='base_rule', sockets=sockets, rarity='normal')
    assert [r['details']['runeword'] for r in rows] == expected
    assert not search(database, base_name='Crystal Sword', kind='base_rule', sockets=sockets, rarity='magic')


def test_runeword_search_can_span_eligible_bases(database):
    rows = search(database, kind='base_rule', runeword='Spirit', sockets=4)
    assert {r['name'] for r in rows} == {'Crystal Sword', 'Broad Sword'}


def test_set_fact_does_not_describe_normal_base(database):
    result = lookup(database, 'Circlet', rarity='normal')
    assert not result['evidence'].get('item_fact')
    assert not result.get('prepared', {}).get('items')


@pytest.mark.parametrize('value', [True, '3', float('nan')])
def test_invalid_skill_threshold_rejected(database, value):
    with pytest.raises(ValueError, match='finite numbers'):
        search(database, property_min={'1577': value})


def test_cli_skill_search_preserves_deciding_property(database, capsys):
    assert main(['--database', str(database), 'search', '--base', 'Cinquedeas', '--property-min', '1577=3']) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1
    assert rows[0]['properties'] == {'1577': 3}


def test_combined_skill_socket_quality_facets_do_not_relax_on_miss(database):
    assert not search(database, base_name='Cinquedeas', properties={'1577': 3}, sockets=3)
    assert not search(database, properties={'1577': 3}, rarity='rare')
