"""Build data/containers.json: the objects that are opened for what they hold, from the installed
game's objects.txt.

    uv run --offline python -m inventory_tracking.macros.build_containers <install>

A container is a row with one of the OperateFn values below that can be selected or struck before it
is operated (`Selectable0`, `IsAttackable0`). The values are told by the rows that carry them: 1 the
caskets, 3 the urns, jars and baskets, 4 the chests (the sparkly one among them), 5 the barrel, 14 the
corpses, crates, loose rocks and hidden stashes, 19 the armour stands, 20 the weapon racks. Left out on
purpose: 7 and 30 (the exploding barrel, cow and chest), 68 (the urn that lets monsters out), the
quest chests (39 to 41, 57 to 59) and the bookshelves (26: scrolls and tomes).
"""

import json
import sys
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import rows
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'containers.json'
OPERATED = frozenset(('1', '3', '4', '5', '14', '19', '20'))


def modes(row: dict[str, str]) -> list[int]:
    """The object modes the row can be selected in, and mode 0 for one that is struck instead."""
    found = {mode for mode in range(8) if row.get(f'Selectable{mode}') == '1'}
    return sorted(found | ({0} if row.get('IsAttackable0') == '1' else set()))


def build(objects: list[dict[str, str]], source: str) -> dict:
    found = {
        row['*ID']: {'class': row['Class'], 'modes': modes(row)}
        for row in objects
        if row.get('OperateFn') in OPERATED and 0 in modes(row)
    }
    return {'source': source, 'containers': found}


def main() -> None:
    game = GameFiles(Path(sys.argv[1]))
    data = build(
        rows(game, 'objects'), 'objects.txt of the installed game: class id -> Class and the modes it can be used in'
    )
    OUTPUT.write_text(json.dumps(data, indent=1) + '\n')
    print(f'{len(data["containers"])} containers -> {OUTPUT}')


if __name__ == '__main__':
    main()
