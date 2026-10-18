"""The Warlock's skills (builds/warlock/skills.py) and what the framework's texts call a skill (macros/skills.py)."""

import ast
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock import skills as warlock
from inventory_tracking.macros import skills
from inventory_tracking.macros.skills import register_names, skill_name


# Every skill by the name the log and the replays have it under (the replay logs hold these strings).
NAMED = {
    377: 'Summon Defiler',
    381: 'Consume',
    379: 'Engorge',
    382: 'Bind Demon',
    387: 'Psychic Ward',
    389: 'Hex: Purge',
    54: 'Teleport',
    390: 'Blade Warp',
    0: 'Attack',
    388: 'Echoing Strike',
    393: 'Sigil: Lethargy',
    375: 'Death Mark',
    -1: 'Swap Weapons',
}


def test_all_thirteen_skills_are_called_what_they_were():
    assert len(NAMED) == 13
    for skill, name in NAMED.items():
        assert skill_name(skill) == name
        assert skills.NAMES[skill] == name
    assert set(NAMED) <= set(skills.NAMES)


def test_a_skill_without_a_name_and_no_skill_are_said_as_before():
    assert skill_name(None) == 'unknown'
    assert skill_name(9999) == 'skill 9999'
    assert skill_name(220) == 'Town Portal'  # any character's, from a tome (macros/portal.py)


def test_the_ids_are_the_ones_the_framework_held():
    assert (warlock.SUMMON_DEFILER, warlock.CONSUME, warlock.ENGORGE, warlock.BIND_DEMON) == (377, 381, 379, 382)
    assert (warlock.PSYCHIC_WARD, warlock.HEX_PURGE, warlock.BLADE_WARP) == (387, 389, 390)
    assert (warlock.ECHOING_STRIKE, warlock.SIGIL_LETHARGY, warlock.DEATH_MARK) == (388, 393, 375)
    assert (skills.TELEPORT, skills.ATTACK, skills.SWAP_WEAPONS) == (54, 0, -1)


def test_every_skill_of_the_warlock_has_a_name_and_none_is_the_frameworks():
    ids = {value for name, value in vars(warlock).items() if name.isupper() and isinstance(value, int)}
    assert ids == set(warlock.NAMES)
    assert len(ids) == 10
    assert ids.isdisjoint({skills.TELEPORT, skills.ATTACK, skills.SWAP_WEAPONS})


def test_the_framework_names_only_the_skills_any_character_has_until_a_build_registers_its_own():
    # What the module holds by itself, read from its source: the registry is filled by whoever loaded a build.
    tree = ast.parse(Path(skills.__file__).read_text(encoding='utf-8'))
    [names] = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NAMES' for t in node.targets)
    ]
    assert isinstance(names, ast.Dict)
    assert [key.id for key in names.keys if isinstance(key, ast.Name)] == [
        'TELEPORT', 'TOWN_PORTAL', 'SLING_TOWN_PORTAL', 'ATTACK', 'SWAP_WEAPONS',
    ]  # fmt: skip
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) and 'builds' in ast.dump(node) for node in tree.body)


def test_a_name_is_registered_once_and_a_second_different_one_is_refused(monkeypatch):
    monkeypatch.setattr(skills, 'NAMES', dict(skills.NAMES))
    register_names({9001: 'Bolt'})
    register_names({9001: 'Bolt'})  # the same again: a module loaded twice
    assert skill_name(9001) == 'Bolt'
    with pytest.raises(ValueError, match='skill 9001 is Bolt already: not also Dart'):
        register_names({9001: 'Dart'})
    with pytest.raises(ValueError, match='skill 54 is Teleport already'):
        register_names({skills.TELEPORT: 'Blink'})
    assert skill_name(9001) == 'Bolt'
