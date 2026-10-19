"""The Warlock's skills: their ids (skills.txt) and their names in the log and to the player, registered with the
framework when this module loads (macros/skills.py `register_names`).
"""

from inventory_tracking.macros.skills import register_names


SUMMON_DEFILER = 377
CONSUME = 381
ENGORGE = 379  # skills.txt: cast on a corpse, heals the pets and lowers the damage they take for a while
BIND_DEMON = 382
PSYCHIC_WARD = 387
HEX_PURGE = 389
BLADE_WARP = 390  # skills.txt: "hurl an astral weapon that teleports you to its impact"; needs a melee weapon
# The hunt keys (macros/hunt.py): Echoing Strike on `7` for Quick Cast (a mouse button is the fallback), Sigil:
# Lethargy on mouse 5.
ECHOING_STRIKE = 388
SIGIL_LETHARGY = 393
DEATH_MARK = 375  # on the strongest monster in reach now and then (user, 2026-10-09 late); `d` for CybergrindAA
NAMES = {
    SUMMON_DEFILER: 'Summon Defiler',
    CONSUME: 'Consume',
    ENGORGE: 'Engorge',
    BIND_DEMON: 'Bind Demon',
    PSYCHIC_WARD: 'Psychic Ward',
    HEX_PURGE: 'Hex: Purge',
    BLADE_WARP: 'Blade Warp',
    ECHOING_STRIKE: 'Echoing Strike',
    SIGIL_LETHARGY: 'Sigil: Lethargy',
    DEATH_MARK: 'Death Mark',
}
register_names(NAMES)
