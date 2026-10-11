"""The threat table (table.py): built from the game's tables, and the scenes use only what it holds."""

import json

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from tests.inventory_tracking.scenarios.threat.scenes import HERALD, HERALD_MINION, SCENES
from tests.inventory_tracking.scenarios.threat.table import (
    EXCEL,
    RECORDED,
    TABLE,
    TERROR_LEVEL,
    build,
    hit,
    multiple,
    row_of,
    table,
)


def test_the_checked_in_table_is_what_the_raw_game_tables_give():
    if not EXCEL.exists():
        pytest.skip('pricing/raw/game-excel is not on this machine (git-ignored)')
    assert json.loads(json.dumps(build())) == json.loads(TABLE.read_text(encoding='utf-8'))


def test_echoing_strike_is_a_weapon_attack_without_an_element():
    assert table()['skill'] == {'id': 388, 'name': 'Echoing Strike', 'src_damage': 116, 'element': ''}


def test_every_type_of_the_recorded_areas_and_every_terror_zone_level_has_a_row():
    found = table()
    assert all(str(area) in found['levels'] for area in RECORDED)
    assert len(found['levels']) == 126
    assert len(found['monsters']) == 330
    assert {row['name'] for row in found['monsters'].values() if row['recorded']} == {
        'Ghoul', 'Afflicted', 'Tainted', 'Dark Shaman', 'Arach', 'The Banished',
        'Storm Caster', 'Oblivion Knight', 'Venom Lord',
    }  # fmt: skip


def test_a_hit_is_the_monstats_percent_of_the_levels_base_damage():
    # Venom Lord: A1 100-160% of monlvl DM(H), 96 at the Chaos Sanctuary's 85 and 107 at the Terror Zone's 95
    assert hit(362, 85) == (96.0, 153.6)
    assert hit(362, TERROR_LEVEL) == (107.0, 171.2)
    assert multiple(362) == 1.6
    assert multiple(118) == pytest.approx(
        1.9 * 0.25 * 5.0
    )  # a Gloam: lightning at 75% resistance, x5 from the probe logs


def test_the_blades_immunities_are_the_physical_resistances():
    rows = table()['monsters'].values()
    assert sum(1 for row in rows if row['resist_physical'] >= 100) == 15
    assert sum(1 for row in rows if 50 <= row['resist_physical'] < 100) == 88  # immune once Stone Skin adds 50
    assert all(
        row['resist_physical'] == int(tables()['monsters'][txt].get('ResDm(H)', 0))
        for txt, row in table()['monsters'].items()
    )


def test_the_terror_zone_rules_are_the_installed_games():
    terror = table()['rules']['terror']
    assert (terror['boost_level'], terror['level_bounds']) == (2, [70, 96])
    assert terror['forced_modifiers'] == {
        '5': 15,
        '6': 15,
        '7': 5,
        '9': 15,
        '17': 10,
        '18': 15,
        '25': 5,
        '27': 5,
        '28': 5,
    }
    assert table()['rules']['modifiers']['28'] == 'stoneskin'
    first = terror['heralds'][0]
    assert (1 + first['life_boost_percent'] / 100, 1 + first['damage_boost_percent'] / 100) == (
        HERALD['life_factor'],
        HERALD['damage_factor'],
    )
    assert (1 + first['minion_life_boost_percent'] / 100, 1 + first['minion_damage_boost_percent'] / 100) == (
        HERALD_MINION['life_factor'],
        HERALD_MINION['damage_factor'],
    )
    assert [tier['minions'] for tier in terror['heralds']] == [6, 8, 10, 12, 14]


@pytest.mark.parametrize('name', SCENES)
def test_a_scenes_monsters_are_a_real_mix_of_its_level(name):
    scene = SCENES[name].scene()
    assert all(scene.area in row_of(h.txt)['areas'] for h in scene.hostiles)
