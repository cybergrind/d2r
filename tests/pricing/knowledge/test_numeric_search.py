"""Numeric discovery stays typed and bounded on a large unrelated corpus."""

import json
import sqlite3

import pytest

from pricing.knowledge.index import build_index, search


@pytest.fixture
def database(tmp_path):
    rows = [{'name': f'Other {i}', 'kind': 'market', 'properties': {'102': i}} for i in range(500)]
    rows.extend(
        {'name': name, 'kind': 'market', 'properties': props}
        for name, props in [
            ('A match', {'101': 3, '102': 8}),
            ('B match', {'101': 3.5, '102': 8}),
            ('C wrong companion', {'101': 4, '102': 2}),
            ('D text', {'101': '3'}),
            ('E boolean', {'101': True}),
            ('F null', {'101': None}),
            ('G large', {'101': 2**60 + 1}),
            ('H neighbor', {'101': 2**60}),
        ]
    )
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    database = tmp_path / 'index.sqlite3'
    build_index([source], database)
    return database


def test_numeric_skill_search_does_not_walk_unrelated_payloads(database):
    with sqlite3.connect(database) as connection:
        steps = []
        connection.set_progress_handler(lambda: steps.append(1) and 0, 100)
        found = search(connection, property_min={'101': 3}, limit=1)
        connection.set_progress_handler(None, 0)
    assert [row['name'] for row in found] == ['A match']
    assert len(steps) < 10, f'Numeric discovery executed at least {len(steps) * 100} VM steps'


@pytest.mark.parametrize(
    'facets',
    [
        {'properties': {'101': 3}},
        {'properties': {'101': True}},
        {'properties': {'101': '3'}},
        {'properties': {'101': 2**60 + 1}},
        {'property_min': {'101': 3.5}},
        {'property_min': {'101': 3, '102': 8}},
        {'properties': {'101': 3}, 'property_min': {'102': 8}},
    ],
)
def test_indexed_numeric_results_equal_legacy_typed_search(database, facets):
    before = search(database, **facets)
    with sqlite3.connect(database) as connection:
        connection.execute('DROP TABLE IF EXISTS evidence_numeric_properties')
    assert search(database, **facets) == before
    if facets == {'properties': {'101': 2**60 + 1}}:
        assert [row['name'] for row in before] == ['G large']
