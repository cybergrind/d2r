import xml.etree.ElementTree as ET

import pytest

from terror_zones.diagnostic import first_spawn
from terror_zones.zone_table import charts_html, hazard_curves, load_zones, spawn_curves, table_html, zone_rows


@pytest.fixture(scope='module')
def table():
    return zone_rows(load_zones())


def test_all_article_groups_present(table):
    assert sum(len(rows) for rows in table.values()) == 74
    assert set(table) == {'1', '2', '3', '4', '5'}


@pytest.mark.parametrize(
    ('act', 'group', 'monsters'),
    [('1', 'Den of Evil', 67), ('1', 'Cow Level', 501), ('5', 'Worldstone Keep and Throne', 580)],
)
def test_rows_match_diagnostic(table, act, group, monsters):
    row = next(r for r in table[act] if r['group'] == group)
    assert row['monsters'] == monsters
    assert row['tier1_chance'] == first_spawn(monsters, 1)['spawn_probability']
    assert row['tier5_chance'] == first_spawn(monsters, 5)['spawn_probability']


def test_rows_sorted_largest_first(table):
    for rows in table.values():
        assert [r['monsters'] for r in rows] == sorted((r['monsters'] for r in rows), reverse=True)


def test_curves_are_monotone_and_bounded():
    for points in hazard_curves().values():
        ys = [y for _, y in points]
        assert ys == sorted(ys)
        assert ys[0] >= 0
        assert ys[-1] <= 4.5
    for points in spawn_curves(120).values():
        ys = [y for _, y in points]
        assert ys == sorted(ys)
        assert ys[-1] <= 100


def test_html_fragments_are_well_formed(table):
    for fragment in (charts_html(), table_html(table)):
        ET.fromstring(f'<root>{fragment}</root>')
    assert charts_html().count('<svg') == 2
    assert table_html(table).count('<tr class="act">') == 5
