"""Herald groups: the article's 74 groups as level ids, each area in at most one group."""

import json
from pathlib import Path

from inventory_tracking.terror.zones import GROUPS, TOMB, group_of


ROOT = Path(__file__).resolve().parents[3]


def test_groups_are_the_article_groups_with_their_populations():
    article = json.loads((ROOT / 'terror_zones/data/article-zones.json').read_text())
    expected = {(int(act), name, population) for act, groups in article['acts'].items() for name, population in groups}
    tombs = {row for row in expected if "Tal Rasha's Tomb" in row[1]}

    assert {(g.act, g.name, g.population) for g in GROUPS if not g.name.startswith(TOMB)} == expected - tombs
    assert len(tombs) == 7
    assert [(g.areas, g.population) for g in GROUPS if g.name.startswith(TOMB)] == [((a,), 124) for a in range(66, 73)]


def test_every_area_is_in_at_most_one_group_and_is_a_real_level():
    levels = json.loads((ROOT / 'third-parties/d2data/json/levels.json').read_text())
    rows = levels if isinstance(levels, list) else list(levels.values())
    known = {row['Id'] for row in rows if row.get('Id')}
    areas = [area for group in GROUPS for area in group.areas]

    assert len(areas) == len(set(areas))
    assert set(areas) <= known


def game_levels():
    """(Terror Zone id, zone_data_id, level id, weight) of every level with a Herald group in the game's file."""
    config = json.loads((ROOT / 'terror_zones/data/desecratedzones-game.json').read_text(encoding='utf-8-sig'))
    return [
        (zone['id'], level['zone_data_id'], level['level_id'], level['zone_completion_weight'])
        for zone in config['desecrated_zones'][0]['zones']
        for level in zone['levels']
        if 'zone_data_id' in level
    ]


def test_groups_levels_and_weights_are_the_installed_games():
    expected = {}
    for zone, zone_data, area, weight in game_levels():
        expected.setdefault((zone, zone_data), {})[area] = weight

    assert {(g.zone, g.zone_data): dict(zip(g.areas, g.weights, strict=True)) for g in GROUPS} == expected


def test_levels_without_a_herald_group_in_the_game_have_none_here():
    for area in (20, 45, 50, 73, 132):  # Forgotten Tower, Valley of Snakes, Harem 1, Duriel's Lair, Worldstone Chamber
        assert group_of(area) is None


def test_tier_curves_and_the_terror_modifier_pool_are_the_installed_games():
    from inventory_tracking.terror.tracker import TERROR_MODIFIERS
    from terror_zones.diagnostic import PARAMETERS

    config = json.loads((ROOT / 'terror_zones/data/desecratedzones-game.json').read_text(encoding='utf-8-sig'))
    hell = config['desecrated_zones'][0]['game_difficulties']['rotw']['hell']
    fields = ('zone_chance_slope', 'zone_chance_midpoint', 'zone_chance_asymptote', 'zone_chance_vertical_shift')
    tiers = {number: tuple(tier[f] for f in fields) for number, tier in enumerate(hell['defaults']['herald_tiers'], 1)}

    assert tiers == PARAMETERS
    assert {mod['unique_mod'] for mod in hell['always_unique_mod_pool']} == TERROR_MODIFIERS


def test_multi_level_groups_count_together_and_single_levels_stay_alone():
    assert group_of(6).name == 'Black Marsh'
    assert group_of(11) is group_of(15)  # Hole levels
    assert group_of(11) is not group_of(6)  # same Terror Zone, separate Herald groups
    assert set(group_of(35).areas) == {32, 33, 34, 35, 36, 37}
    assert group_of(1) is None  # Rogue Encampment
