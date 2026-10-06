"""The key that casts a skill, for the character in the game: skill id -> slot -> key.

The slot comes from the game's memory (world.py), the key from the character's own key file
(input/keybindings.py). Slot `i` is key action `14 + i` for the first eight slots and
`46 + (i - 8)` after them (record probe, 2026-10-06: the four keys the user named agree).
"""

from pathlib import Path

from inventory_tracking.input.keybindings import MODIFIERS, action_keys, key_file, x11_name


SUMMON_DEFILER = 377
CONSUME = 381
BIND_DEMON = 382
PSYCHIC_WARD = 387
HEX_PURGE = 389
NAMES = {
    SUMMON_DEFILER: 'Summon Defiler',
    CONSUME: 'Consume',
    BIND_DEMON: 'Bind Demon',
    PSYCHIC_WARD: 'Psychic Ward',
    HEX_PURGE: 'Hex: Purge',
}


def slot_action(slot: int) -> int:
    return 14 + slot if slot < 8 else 46 + slot - 8


def skill_keys(slots, bindings: bytes, skills) -> dict[int, str]:
    """X11 key name per wanted skill id; ValueError names the first skill without a pressable key."""
    keys = {}
    for skill in skills:
        name = NAMES.get(skill, f'skill {skill}')
        if skill not in slots:
            raise ValueError(f'{name} is not on a skill key')
        codes = action_keys(bindings, slot_action(slots.index(skill)))
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
