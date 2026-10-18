"""Which carried items are the loop's and which the player's: the inventory's volatile cells (the player, 2026-10-19:
"cube is volatile; empty cells on the start of character - are volatile; then, you have to remember what cells are
volatile and do not lose this when we restart game, reload `make serve` or for other reasons").

- The cube is volatile: everything in it is the loop's (cube.py `loot` and the visit take `pack.in_cube` whole).
- An inventory cell is volatile when the character's inventory left it empty at its start (the seed): an item lying
  only on volatile cells is the loop's; an item on any protected cell is the player's, never moved, stashed, sold or
  dropped by a macro.
- The cells are kept per character in STORE_FILE (beside the loop's other files, runs/alt-d/): a new game, a restart
  of the service and a loop toggle all read the same cells. Only `reset` (the player's rearranged charms) forgets them;
  the next loop start seeds them again from the inventory as it is then.

A second line of defence for what cannot be undone: the stats of every item seen on a protected cell are kept too
(`prints`). An item whose stats match one of them is the player's wherever it lies, in the cube too (the player's charms
moved into the cube by hand were sold at 23:17 on 2026-10-18: rca/2026-10-18/player-items-moved-findings.md): a visit
never counts it junk, and Jamella and the ground never get it.

    uv run --offline python -m inventory_tracking.macros.volatile show
    uv run --offline python -m inventory_tracking.macros.volatile reset CybergrindAA
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.macros.world import Carried, Pack


STORE_FILE = 'volatile-cells.json'
SERVE_DIR = Path(__file__).resolve().parents[1] / 'runs' / 'alt-d'  # `make serve`'s output (loop-items.json)
GRID = (10, 4)  # the inventory's columns and rows
# Stats that change while an item is carried and so tell nothing about which item it is: its quantity and durability
QUANTITY, DURABILITY = 70, 72
CHANGING = frozenset({QUANTITY, DURABILITY})

Cell = tuple[int, int]
Print = tuple[int, int, tuple[tuple[int, int], ...]]  # class, quality, the stats (id, raw value) sorted


def cells_of(item: Carried) -> frozenset[Cell]:
    return frozenset(
        (item.x + dx, item.y + dy) for dx in range(item.size[0]) for dy in range(item.size[1])
    )  # fmt: skip


def print_of(item: Carried, stats: Mapping[int, int]) -> Print:
    return item.txt, item.quality, tuple(sorted((int(k), int(v)) for k, v in stats.items() if k not in CHANGING))


@dataclass
class Volatile:
    """The store (STORE_FILE) of every character's protected cells and the prints of the items seen on them."""

    path: Path | None

    def _read(self) -> dict:
        if self.path is None or not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except OSError, ValueError:
            return {}

    def _write(self, data: dict) -> None:
        if self.path is None:
            return
        try:
            self.path.write_text(json.dumps(data, indent=1, sort_keys=True))
        except OSError as error:
            LOG.info('Macro: volatile cells: not kept in %s: %s', self.path, error)

    def protected(self, name: str | None) -> frozenset[Cell] | None:
        """The character's protected cells (those not volatile); None when it has none kept (not seeded)."""
        entry = self._read().get(name) if name is not None else None
        if not isinstance(entry, dict) or not isinstance(entry.get('protected'), list):
            return None
        try:
            return frozenset((int(x), int(y)) for x, y in entry['protected'])
        except TypeError, ValueError:
            return None

    def seed(self, name: str, items: Iterable[Carried], why: str) -> frozenset[Cell]:
        """The cells `items` (the player's, as the character starts) cover, kept as the character's protected cells;
        every other inventory cell is volatile from now on. The key stack's cell is the player's too (the player,
        2026-10-19: the volatile cells are the 2 x 4 block and the 2 x 1 left of it)."""
        cells = frozenset(c for item in items for c in cells_of(item))
        data = self._read()
        found = data.get(name)
        old: dict = found if isinstance(found, dict) else {}
        data[name] = {
            'protected': sorted(cells),
            'seeded': datetime.now().isoformat(timespec='seconds'),
            'why': why,
            'prints': old.get('prints', []),
        }
        self._write(data)
        LOG.info('Macro: volatile cells: seeded for %s (%s): %d protected, %d volatile: %s', name, why, len(cells),
                 GRID[0] * GRID[1] - len(cells), picture(cells))  # fmt: skip
        return cells

    def prints(self, name: str | None) -> frozenset[Print]:
        entry = self._read().get(name) if name is not None else None
        if not isinstance(entry, dict):
            return frozenset()
        try:
            return frozenset((int(t), int(q), tuple((int(k), int(v)) for k, v in s)) for t, q, s in entry['prints'])
        except KeyError, TypeError, ValueError:
            return frozenset()

    def learn(self, name: str, found: Iterable[Print]) -> int:
        """`found` (the prints of the items on protected cells) added to the character's; how many were new."""
        known = self.prints(name)
        new = [p for p in found if p not in known]
        if not new:
            return 0
        data = self._read()
        kept = data.get(name)
        entry: dict = kept if isinstance(kept, dict) else {}
        entry['prints'] = [[t, q, [list(s) for s in stats]] for t, q, stats in sorted({*known, *new})]
        data[name] = entry
        self._write(data)
        return len(new)

    def reset(self, name: str) -> bool:
        data = self._read()
        if name not in data:
            return False
        del data[name]
        self._write(data)
        return True


def own_of(pack: Pack, protected: frozenset[Cell]) -> frozenset[tuple[int, int, int]]:
    """The player's items in the inventory, by class and cell (cube.py `loot`'s `own`): those on a protected cell."""
    return frozenset((i.txt, i.x, i.y) for i in pack.items if cells_of(i) & protected)


def empty(pack: Pack, protected: frozenset[Cell]) -> frozenset[Cell]:
    """The protected cells no item covers now: a pickup the game puts there is read as the player's."""
    taken = {c for i in pack.items for c in cells_of(i)}
    return frozenset(protected - taken)


def picture(protected: frozenset[Cell]) -> str:
    """The grid as rows: '#' protected, '.' volatile."""
    return '/'.join(''.join('#' if (x, y) in protected else '.' for x in range(GRID[0])) for y in range(GRID[1]))


def is_players(item: Carried, stats: Mapping[int, int], prints: frozenset[Print]) -> bool:
    """Whether `item` is one of the player's by its stats (`prints`). Stats unread (`stats` empty): the player's when
    any of theirs is of its class and quality, for a sale or a drop cannot be undone."""
    if not prints:
        return False
    if not stats:
        return any(p[0] == item.txt and p[1] == item.quality for p in prints)
    return print_of(item, stats) in prints


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='The inventory volatile cells kept per character.')
    parser.add_argument('action', choices=('show', 'reset'))
    parser.add_argument('name', nargs='?')
    parser.add_argument('--dir', type=Path, default=SERVE_DIR, help='where serve keeps the loop files')
    args = parser.parse_args(argv)
    store = Volatile(args.dir / STORE_FILE)
    data = store._read()
    if args.action == 'reset':
        if not args.name:
            parser.error('reset needs the character name')
        done = store.reset(args.name)
        print(f'{args.name}: {"forgotten; the next loop start seeds the cells again" if done else "none kept"}')
        return 0
    for name in [args.name] if args.name else sorted(data):
        cells = store.protected(name)
        if cells is None:
            print(f'{name}: none kept')
            continue
        entry = data[name]
        print(f'{name}: seeded {entry.get("seeded")} ({entry.get("why")}); {len(store.prints(name))} item prints')
        for row in picture(cells).split('/'):
            print('   ', row)
    return 0


if __name__ == '__main__':
    sys.exit(main())
