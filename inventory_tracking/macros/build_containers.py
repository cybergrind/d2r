"""Build data/containers.json (objects opened for loot) from the installed game's objects.txt.

    uv run --offline python -m inventory_tracking.macros.build_containers <install>

A container: an OPERATED OperateFn row selectable or attackable in mode 0. OperateFn 1 caskets, 3 urns/jars/baskets,
4 chests, 5 barrel, 14 corpses/crates/rocks/stashes, 19 armour stands, 20 weapon racks. Left out: 7 and 30
(exploding), 68 (monster urn), quest chests (39-41, 57-59), bookshelves (26).
"""

import json
import sys
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import rows
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'containers.json'
OPERATED = frozenset(('1', '3', '4', '5', '14', '19', '20'))


def modes(row: dict[str, str]) -> list[int]:
    """Modes the row is selectable in, plus 0 when it is attackable."""
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
