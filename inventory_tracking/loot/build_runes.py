"""Regenerate loot/data/runes.json from the item decoder's d2data copy (a build input only).

Class IDs come from the game's `classid` column (pricing/raw/d2data/misc.json), the source the
item decoder uses to name real inventory items (items/build_metadata.py). The earlier rule
"third-parties misc.json lineNumber + 523" matched keys, tomes and potions but was one too high
for runes: the user saw Ist named Mal and Mal named Um (2026-09-30).
Run: uv run --offline python -m inventory_tracking.loot.build_runes
"""

import json
from pathlib import Path

from inventory_tracking.reports import publish


MISC = Path('pricing/raw/d2data/misc.json')
OUTPUT = Path(__file__).parent / 'data' / 'runes.json'


def build(misc_path: Path) -> dict:
    misc = json.loads(misc_path.read_text())
    runes = {f'r{n:02d}': misc[f'r{n:02d}'] for n in range(1, 34)}
    return {
        'source': f'{misc_path} (game classid column, as the item decoder uses)',
        'runes': {str(row['classid']): {'code': code, 'name': row['name']} for code, row in runes.items()},
    }


def main():
    publish(OUTPUT, build(MISC))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
