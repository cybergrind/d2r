"""Regenerate levels/data/warp_boxes.json: where each door takes a click, from lvlwarp.txt.

A door (a warp tile unit, unit type 5) takes clicks in a box of classic pixels (600 high) hung
from the unit's own place on screen: SelectX, SelectY to its top left corner, SelectDX, SelectDY
its size. The unit's class is the row's Id. Checked on 2026-10-10 against the running game: the
tower's door in Black Marsh (Id 10, box -10, -50, 150 x 80) stood 6.5, 2.5 units "north-west" of
the centre of its warp tiles, which puts the box 42 to 122 pixels above that centre; of the aims
clicked there that day the one on the tiles never took and those 45 pixels above took 5 times of 9.
An Id with a left and a right row (the Act 5 temples) keeps the part both boxes share; a row
without a size, or two rows that share nothing, is left out.

Runtime code reads only the bundled table; the git-ignored checkout is a build input.
Run: uv run --offline python -m inventory_tracking.levels.build_warp_boxes
"""

import json
from pathlib import Path

from inventory_tracking.levels.build_presets import D2DATA
from inventory_tracking.reports import publish


OUTPUT = Path(__file__).parent / 'data' / 'warp_boxes.json'


def build(rows) -> dict:
    """`rows`: the lvlwarp rows. Id -> [left, top, right, bottom] of the box all its rows share."""
    boxes: dict[int, list[int]] = {}
    empty = set()
    for row in rows:
        left, top = row['SelectX'], row['SelectY']
        box = [left, top, left + row['SelectDX'], top + row['SelectDY']]
        known = boxes.get(row['Id'], box)
        shared = [max(known[0], box[0]), max(known[1], box[1]), min(known[2], box[2]), min(known[3], box[3])]
        if shared[0] >= shared[2] or shared[1] >= shared[3]:
            empty.add(row['Id'])
        boxes[row['Id']] = shared
    return {
        'source': 'blizzhackers/d2data json/lvlwarp.json',
        'boxes': {str(found): box for found, box in sorted(boxes.items()) if found not in empty},
    }


def main():
    publish(OUTPUT, build(json.loads((D2DATA / 'json' / 'lvlwarp.json').read_text()).values()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
