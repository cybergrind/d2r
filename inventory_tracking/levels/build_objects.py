"""Regenerate levels/data/preset_objects.json: where each preset's files place the objects a mark may sit on.

For every LvlPrest Def and DS1 variant (File1.. order, 0-based as Room.variant): the objects of the
WANTED kinds (objects.txt ids, through objpreset.txt), each at its place in world units from the
preset origin. `variants` counts the files of every preset that holds one, so a mark can be checked
to have a spot in each layout (levels/registry.py). Reads the d2data checkout (third-parties/) for
the tables and the installed game (read-only) for the files. Runtime code reads only the bundled table.

Run: uv run --offline python -m inventory_tracking.levels.build_objects "<game folder>"
"""

import argparse
import json
from pathlib import Path

from inventory_tracking.levels.build_presets import D2DATA
from inventory_tracking.levels.build_warps import VARIANTS, game_path
from inventory_tracking.levels.ds1 import object_presets
from inventory_tracking.levels.model import MARKABLE
from inventory_tracking.reports import publish
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'preset_objects.json'


def wanted_rows(d2data: Path, wanted=MARKABLE) -> dict[tuple[int, int], int]:
    """(act, 0-based; objpreset Index) -> the objects.txt id of every wanted object."""
    objects = json.loads((d2data / 'json' / 'objects.json').read_text())
    ids = {row['Class']: row['*ID'] for row in objects.values() if row.get('*ID') in wanted and row.get('Class')}
    rows = json.loads((d2data / 'json' / 'objpreset.json').read_text())
    return {
        (row['Act'] - 1, row['Index']): ids[row['ObjectClass']]
        for row in rows.values()
        if row.get('ObjectClass') in ids
    }


def build(d2data: Path, read, wanted=MARKABLE) -> dict:
    presets = json.loads((d2data / 'json' / 'lvlprest.json').read_text())
    rows = wanted_rows(d2data, wanted)
    placed: dict[str, dict[str, list[list[int]]]] = {}
    variants: dict[str, int] = {}
    for preset in presets.values():
        if 'Def' not in preset:
            continue
        names = [preset.get(f'File{variant + 1}') for variant in range(VARIANTS)]
        files = [(variant, name) for variant, name in enumerate(names) if name and name != '0']
        for variant, name in files:
            act, objects = object_presets(read(game_path(name)))
            found = [[rows[act, index], x, y] for index, x, y in objects if (act, index) in rows]
            if found:
                placed.setdefault(str(preset['Def']), {})[str(variant)] = found
        if str(preset['Def']) in placed:
            variants[str(preset['Def'])] = len(files)
    return {
        'source': 'installed game DS1 files (data/global/tiles) named by d2data json/lvlprest.json; '
        'objects by d2data json/objpreset.json and json/objects.json',
        'objects': placed,
        'variants': variants,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    publish(OUTPUT, build(D2DATA, GameFiles(args.install).read))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
