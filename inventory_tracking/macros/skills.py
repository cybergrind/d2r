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
TELEPORT = 54  # from a charged staff or an oskill alike; the slot table holds it either way
# The hunt keys (macros/hunt.py). Echoing Strike was in no slot of CybergrindAA until the user put it
# on `7` (2026-10-09 evening) so that Quick Cast casts it at the pointer like any skill; before that
# it was on a mouse button, which the hunt still falls back to. Sigil: Lethargy sits on mouse 5.
ATTACK = 0  # the plain attack, what a mouse button holds when no skill is on it
ECHOING_STRIKE = 388
SIGIL_LETHARGY = 393
DEATH_MARK = 375  # on the strongest monster in reach now and then (user, 2026-10-09 late); `d` for CybergrindAA
# Not a skill: the Swap Weapons key action. CybergrindAA has `c` on action 44 and says `c`
# swaps (user, 2026-10-06); unconfirmed against another character's file.
SWAP_WEAPONS = -1
ACTIONS = {SWAP_WEAPONS: 44}
NAMES = {
    SUMMON_DEFILER: 'Summon Defiler',
    CONSUME: 'Consume',
    BIND_DEMON: 'Bind Demon',
    PSYCHIC_WARD: 'Psychic Ward',
    HEX_PURGE: 'Hex: Purge',
    TELEPORT: 'Teleport',
    ATTACK: 'Attack',
    ECHOING_STRIKE: 'Echoing Strike',
    SIGIL_LETHARGY: 'Sigil: Lethargy',
    DEATH_MARK: 'Death Mark',
    SWAP_WEAPONS: 'Swap Weapons',
}


def skill_name(skill: int | None) -> str:
    return 'unknown' if skill is None else NAMES.get(skill, f'skill {skill}')


def slot_action(slot: int) -> int:
    return 14 + slot if slot < 8 else 46 + slot - 8


def skill_keys(slots, bindings: bytes, skills) -> dict[int, str]:
    """X11 key name per wanted skill id; ValueError names the first skill without a pressable key."""
    keys = {}
    for skill in skills:
        name = NAMES.get(skill, f'skill {skill}')
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
