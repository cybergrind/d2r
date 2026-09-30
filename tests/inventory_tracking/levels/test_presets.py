"""Bundled LvlPrest/level table: runtime names come from here, never from third-parties/."""

from inventory_tracking.levels.presets import level_name, preset_name


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
