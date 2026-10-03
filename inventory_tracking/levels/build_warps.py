"""Regenerate levels/data/preset_warps.json: where each preset's warps are, from the game's DS1 files.

For every LvlPrest Def and DS1 variant (File1.. order, 0-based as Room.variant) with warp tiles
(levels/ds1.py): slot -> the centre of its tiles, in tiles from the preset origin. Reads the
d2data checkout (third-parties/) for the file names and the installed game (read-only) for the
files themselves. Runtime code reads only the bundled table.

Run: uv run --offline python -m inventory_tracking.levels.build_warps "<game folder>"
"""

import argparse
import json
from pathlib import Path

from inventory_tracking.levels.build_presets import D2DATA
from inventory_tracking.levels.ds1 import warp_tiles
from inventory_tracking.reports import publish
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'preset_warps.json'
VARIANTS = 6  # lvlprest File1..File6


def game_path(name: str) -> str:
    """lvlprest 'Act1/Caves/CaveDr1.ds1' -> the game's 'data/global/tiles/act1/caves/cavedr1.ds1'."""
    return 'data/global/tiles/' + name.replace('\\', '/').lower()


def centre(tiles: list[tuple[int, int]]) -> list[float]:
    return [sum(x for x, _ in tiles) / len(tiles) + 0.5, sum(y for _, y in tiles) / len(tiles) + 0.5]


def build(d2data: Path, read) -> dict:
    presets = json.loads((d2data / 'json' / 'lvlprest.json').read_text())
    warps: dict[str, dict[str, dict[str, list[float]]]] = {}
    for preset in presets.values():
        if 'Def' not in preset:
            continue
        for variant in range(VARIANTS):
            name = preset.get(f'File{variant + 1}')
            if not name or name == '0':
                continue
            slots = warp_tiles(read(game_path(name)))
            if slots:
                warps.setdefault(str(preset['Def']), {})[str(variant)] = {
                    str(slot): centre(tiles) for slot, tiles in sorted(slots.items())
                }
    return {
        'source': 'installed game DS1 files (data/global/tiles) named by d2data json/lvlprest.json',
        'warps': warps,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    publish(OUTPUT, build(D2DATA, GameFiles(args.install).read))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
