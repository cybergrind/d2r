"""Boss levels that are one fixed preset: the mark is where the level's file places the boss.

Super uniques from terror/data/elites.json (`boss=`); Andariel, Duriel and Baal from levels/ds1.py
`monster_presets` (Andy3.ds1, Duriel.ds1, wstone01.ds1; Duriel's read from the installed game on 2026-10-21).
"""

from inventory_tracking.levels.handler import target


HANDLERS = [
    target('Catacombs 4', areas={37}, label='Andariel', preset=r'Act 1 - Andariel', at=(46, 46)),
    # The lair is one preset, the whole level (lvlprest 481): Duriel where its file places him, 135, 218
    target("Duriel's Lair", areas={73}, label='Duriel', preset=r"Act 2 - Duriel's Lair", at=(135, 218)),
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
