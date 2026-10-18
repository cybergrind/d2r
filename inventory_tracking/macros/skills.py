"""The key that casts a skill, for the character in the game: skill id -> slot -> key.

The slot comes from the game's memory (world.py), the key from the character's own key file
(input/keybindings.py). Slot `i` is key action `14 + i` for the first eight slots and
`46 + (i - 8)` after them (record probe, 2026-10-06: the four keys the user named agree).
"""

from collections.abc import Mapping
from pathlib import Path

from inventory_tracking.input.keybindings import MODIFIERS, action_keys, key_file, x11_name


TELEPORT = 54  # from a charged staff or an oskill alike; the slot table holds it either way
TOWN_PORTAL = 220  # Book of Townportal: a tome in the inventory puts it in the slot table (macros/portal.py)
# Townportal O Skill (skills.txt 411, no mana, no delay): the Sling's oskill (uniqueitems.txt Sling, a Ring: `oskill`
# "Townportal O Skill" 1), in place of the tome (the player, 2026-10-18; macros/portal.py `FROM_SLING`)
SLING_TOWN_PORTAL = 411
ATTACK = 0  # the plain attack, what a mouse button holds when no skill is on it
# Not a skill: the Swap Weapons key action. CybergrindAA has `c` on action 44 and says `c`
# swaps (user, 2026-10-06); unconfirmed against another character's file.
SWAP_WEAPONS = -1
ACTIONS = {SWAP_WEAPONS: 44}
# What a skill is called in the log and to the player. Here the ones any character has; a build's own
# are added by the build (`register_names`: builds/warlock/skills.py), which this module never imports.
NAMES = {
    TELEPORT: 'Teleport',
    TOWN_PORTAL: 'Town Portal',
    SLING_TOWN_PORTAL: 'Town Portal (Sling)',
    ATTACK: 'Attack',
    SWAP_WEAPONS: 'Swap Weapons',
}


def register_names(names: Mapping[int, str]) -> None:
    """A build's skills by name, for the texts: called by the module that defines the build's skill
    ids, so whatever can name one of them has its name here. A skill that has a name keeps it: a
    second, different one is an error."""
    for skill, name in names.items():
        if NAMES.setdefault(skill, name) != name:
            raise ValueError(f'skill {skill} is {NAMES[skill]} already: not also {name}')


def skill_name(skill: int | None) -> str:
    return 'unknown' if skill is None else NAMES.get(skill, f'skill {skill}')


def slot_action(slot: int) -> int:
    return 14 + slot if slot < 8 else 46 + slot - 8


def skill_keys(slots, bindings: bytes, skills) -> dict[int, str]:
    """X11 key name per wanted skill id; ValueError names the first skill without a pressable key."""
    keys = {}
    for skill in skills:
        name = skill_name(skill)
        if skill not in ACTIONS and skill not in slots:
            raise ValueError(f'{name} is not on a skill key')
        codes = action_keys(bindings, ACTIONS.get(skill) or slot_action(slots.index(skill)))
        key = next((k for k in map(x11_name, codes) if k and k not in MODIFIERS), None)
        if key is None:
            raise ValueError(f'{name} has no key the macro can press')
        keys[skill] = key
    return keys


def character_bindings(saved_games: Path, name: str) -> bytes:
    path = key_file(saved_games, name)
    if path is None:
        raise ValueError(f'no key file for {name}')
    return path.read_bytes()
