"""Regenerate loot/data/sizes.json: the cells an item of each class takes in the inventory.

weapons.txt, armor.txt and misc.txt give `invwidth` and `invheight` per item code; the item class
ID is the decoder's (items/metadata.py bases). The pickup step reads it to leave alone a drop the
inventory has no room for (macros/pickup.py; user, 2026-10-10 night).

Runtime code reads only the bundled table; the install is a build input.
Run: uv run --offline python -m inventory_tracking.loot.build_sizes "<install>"
"""

import argparse
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish
from inventory_tracking.terror.build_threats import EXCEL, table
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'sizes.json'
TABLES = ('weapons', 'armor', 'misc')


def build(tables: dict[str, list[dict[str, str]]], bases: dict[str, dict], source: str) -> dict:
    by_code = {
        row['code']: [int(row['invwidth']), int(row['invheight'])]
        for rows in tables.values()
        for row in rows
        if row.get('code') and row.get('invwidth') and row.get('invheight')
    }
    sizes = {class_id: by_code[base['code']] for class_id, base in bases.items() if base['code'] in by_code}
    return {'source': source, 'sizes': sizes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    game = GameFiles(args.install)
    tables = {name: table(game.read(EXCEL.format(name)).decode('latin-1')) for name in TABLES}
    publish(
        OUTPUT, build(tables, metadata()['bases'], 'D2R install data/global/excel weapons, armor, misc (2026-10-10)')
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
