"""Build data/waypoints.json: the waypoint panel's tab and row of every level with a waypoint, from levels.txt.

    uv run --offline python -m inventory_tracking.macros.build_waypoints <install>

levels.txt numbers the waypoints in panel order (`Waypoint`, 255 none); the tab is the level's `Act`, the row its
place after the act's first waypoint (the town's).
"""

import json
import sys
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import rows
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'waypoints.json'
NO_WAYPOINT = 255


def build(levels: list[dict[str, str]], source: str) -> dict:
    found = sorted(
        (int(row['Waypoint']), int(row['Id']), int(row['Act']))
        for row in levels
        if row.get('Id', '').isdigit() and row.get('Waypoint', '').isdigit() and int(row['Waypoint']) != NO_WAYPOINT
    )
    first = {}
    for index, _area, act in found:
        first.setdefault(act, index)
    return {
        'source': source,
        'waypoints': {str(area): {'act': act, 'row': index - first[act]} for index, area, act in found},
    }


def main() -> None:
    game = GameFiles(Path(sys.argv[1]))
    data = build(rows(game, 'levels'), 'levels.txt of the installed game: area -> waypoint panel tab (act) and row')
    OUTPUT.write_text(json.dumps(data, indent=1) + '\n')
    print(f'{len(data["waypoints"])} waypoints -> {OUTPUT}')


if __name__ == '__main__':
    main()
