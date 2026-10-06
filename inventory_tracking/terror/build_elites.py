"""Regenerate terror/data/elites.json: how many elite groups a level has, and which are fixed.

Random groups: levels.txt `MonUMin(H)` / `MonUMax(H)`, the Hell range of unique and champion
groups the game rolls per level. Fixed groups come on top of them and are placed by the map
pieces (levels/ds1.py monster objects, named by monpreset.txt): a super unique, a unique pack
(`place_unique_pack`) or a champion group (`place_champion`), each at its spot in the piece.
Probe logs against level evidence, 2026-10-06: the Travincal council, Coldcrow and Corpsefire
were first seen 1-21 units from their object, fixed unique packs 2-11, champion groups 0-4.
Bosses a script spawns are in no piece: SCRIPTED lists those the logs showed (the seal bosses
36-38 in the Chaos Sanctuary, Baal's waves 61-65 in the Throne of Destruction).

Runtime code reads only the bundled table; the install and the d2data checkout are build inputs.
Run: uv run --offline python -m inventory_tracking.terror.build_elites "<install>"
"""

import argparse
import json
from pathlib import Path

from inventory_tracking.levels.build_presets import D2DATA
from inventory_tracking.levels.build_warps import VARIANTS, game_path
from inventory_tracking.levels.ds1 import monster_presets
from inventory_tracking.reports import publish
from inventory_tracking.terror.build_threats import EXCEL, STRINGS, table
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'elites.json'
TABLES = ('levels', 'monpreset', 'superuniques')
PLACES = {'place_unique_pack': 'unique', 'place_champion': 'champion'}
# Level -> superuniques.txt `Superunique` of the bosses a script spawns there.
SCRIPTED = {
    108: ('Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls'),
    131: ('Baal Subject 1', 'Baal Subject 2', 'Baal Subject 3', 'Baal Subject 4', 'Baal Subject 5'),
}


def build(tables: dict[str, list[dict[str, str]]], pieces: dict, names: dict[str, str], source: str) -> dict:
    """`pieces`: (LvlPrest Def, DS1 variant) -> ds1.monster_presets of that file."""
    supers = {row['Superunique']: row for row in tables['superuniques'] if row.get('hcIdx')}

    def shown(key: str) -> str:
        return names.get(supers[key]['Name'], key)

    places: dict[int, list[str]] = {}  # act, 1-based -> its monpreset rows in order
    for row in tables['monpreset']:
        places.setdefault(int(row['Act']), []).append(row['Place'])
    presets: dict[str, dict[str, list[list]]] = {}
    for (preset, variant), (act, objects) in pieces.items():
        rows = places.get(act + 1, [])
        found = []
        for index, x, y in objects:
            place = rows[index] if index < len(rows) else ''
            if place in supers:
                found.append(['super', shown(place), x, y])
            elif place in PLACES:
                found.append([PLACES[place], '', x, y])
        if found:
            presets.setdefault(str(preset), {})[str(variant)] = found
    return {
        'source': source,
        'levels': {
            row['Id']: [int(row['MonUMin(H)']), int(row['MonUMax(H)'])]
            for row in tables['levels']
            if row.get('Id') and row.get('MonUMax(H)')
        },
        'presets': presets,
        'scripted': {
            str(area): [shown(key) for key in keys if key in supers]
            for area, keys in SCRIPTED.items()
            if any(key in supers for key in keys)
        },
        'supers': {row['hcIdx']: shown(key) for key, row in supers.items()},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    game = GameFiles(args.install)
    tables = {name: table(game.read(EXCEL.format(name)).decode('latin-1')) for name in TABLES}
    names = {entry['Key']: entry['enUS'] for entry in json.loads(game.read(STRINGS).decode('utf-8-sig'))}
    pieces = {}
    for preset in json.loads((D2DATA / 'json' / 'lvlprest.json').read_text()).values():
        for variant in range(VARIANTS):
            name = preset.get(f'File{variant + 1}')
            if 'Def' in preset and name and name != '0':
                pieces[preset['Def'], variant] = monster_presets(game.read(game_path(name)))
    source = 'D2R install data/global/excel levels, monpreset, superuniques and data/global/tiles (2026-10-06)'
    publish(OUTPUT, build(tables, pieces, names, source))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
