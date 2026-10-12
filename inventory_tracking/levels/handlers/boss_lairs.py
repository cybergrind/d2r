"""Boss levels that are one fixed preset: the mark is where the level's file places the boss.

Unconfirmed (2026-10-12, levels/routes.md Phase 6; no evidence yet). The super uniques come from
the elite table (terror/data/elites.json, `boss=`). Andariel and Baal are monsters of their own,
not super uniques, so their places are read from the installed game's files with levels/ds1.py
`monster_presets` on 2026-10-12: Act1/Catacomb/Andy3.ds1 places `andariel` at (46, 46),
Expansion/baalLair/wstone01.ds1 places `baalcrab` at (135, 160), in world units from the preset's
origin. The Ruined Temple is the one Kurast temple with a super unique (three layouts).
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target('Catacombs 4', areas={37}, label='Andariel', preset=r'Act 1 - Andariel', at=(46, 46)),
    target('Claw Viper Temple 2', areas={61}, label='Fangskin', preset=r'Act 2 - Tomb Tainted Sun X', boss='Fangskin'),
    target(
        'Ruined Temple',
        areas={94},
        label='Battlemaid Sarina',
        preset=r'Act 3 - Temple 1',
        boss='Battlemaid Sarina',
    ),
    target('Worldstone Chamber', areas={132}, label='Baal', preset=r'Act 5 - WorldStone', at=(135, 160)),
]
