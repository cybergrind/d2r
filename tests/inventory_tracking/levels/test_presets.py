"""Bundled LvlPrest/level table: runtime names come from here, never from third-parties/."""

from inventory_tracking.levels.presets import level_name, open_passage, preset_name


def test_preset_names_cover_every_arcane_summoner_orientation():
    assert [preset_name(d) for d in (525, 526, 527, 528)] == [
        'Act 2 - Arcane Summoner W',
        'Act 2 - Arcane Summoner E',
        'Act 2 - Arcane Summoner S',
        'Act 2 - Arcane Summoner N',
    ]


def test_level_names_are_the_in_game_names():
    assert (level_name(74), level_name(123), level_name(21)) == (
        'Arcane Sanctuary',
        "Halls of Death's Calling",
        'Tower Cellar Level 1',
    )


def test_unknown_ids_have_readable_fallbacks():
    assert (preset_name(99999), level_name(99999)) == ('preset 99999', 'area 99999')


def test_an_open_passage_is_a_level_link_with_no_warp_behind_it_or_a_border():
    """levels.txt (2026-10-15): the River of Flame's Vis1 is the Chaos Sanctuary with Warp1 -1, entered by walking
    across the bridge's end; the City of the Damned's way into the River is a warp (69). The Cold Plains name no Vis
    slot for the Burial Grounds: a border, walked across too."""
    passages = [(107, 108), (108, 107), (27, 28), (32, 33)]  # the River's bridge, the Outer Cloister's gate, ...
    borders = [(3, 17), (104, 105)]
    warps = [(106, 107), (2, 8), (46, 66), (120, 128)]  # stairs into the River, a cave, a tomb, the Keep's door
    assert [open_passage(*pair) for pair in (*passages, *borders)] == [True] * 6
    assert [open_passage(*pair) for pair in warps] == [False] * 4
