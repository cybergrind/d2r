"""The recorded town visits (macros/visitlog.py `visits/<HHMMSS>.json`) replayed through the storage planning, for
loot/design.md §7 step M3: the planning moved from macros/cube.py and macros/town.py into loot/storage.py must plan
every recorded stop as before, byte for byte.

`plans` runs one snapshot through a `town` and a `cube` module and returns every plan in a canonical JSON form (the
same text whichever module's classes made it); `old_modules` loads the two modules (and the stash's) as they were
before the move, from git (OLD_COMMIT), so a replay compares old and new code directly. `old_room` is the loop's room
count as `Loop.look` computed it before M3 (macros/loop.py at OLD_COMMIT, verbatim).

The golden plans of the kept fixtures (fixtures/visits/plans.json, each plan's SHA-256 of its canonical text) were
written by the code at OLD_COMMIT:

    uv run --offline python -c "from tests.inventory_tracking.loot.visit_replay import write; write()"

(only meaningful with the old code; after the move it would write the new code's plans).
"""

import dataclasses
import enum
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

from inventory_tracking.game.records import Pack
from inventory_tracking.items.grid import Grid
from inventory_tracking.macros.visitlog import Snapshot, load


OLD_COMMIT = '8c7b1c3'  # the last commit before M3 (2026-10-20): cube.py, town.py and stash.py as they were
ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).parent / 'fixtures' / 'visits'
GOLDEN = FIXTURES / 'plans.json'
RUNS = ROOT / 'inventory_tracking' / 'runs' / 'alt-d'
INVENTORY_CELLS = 40  # macros/stash.py INVENTORY_CELLS at OLD_COMMIT (10 x 4)
TRADE_ROOM = 8  # macros/town.py at OLD_COMMIT
SURE_BLOCK = (1, 3)  # macros/cube.py at OLD_COMMIT


# Fields added after the golden plans were written, left out at their default so the plans still compare byte for
# byte (D12, 2026-10-23: game/records.py Carried.runeword)
LATER_FIELDS = frozenset({('Carried', 'runeword')})


def canon(value: Any) -> Any:
    """`value` as plain JSON data: a dataclass as its type's name and fields, a set sorted, a mapping's keys as text."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        name = type(value).__name__
        fields = {f.name: canon(getattr(value, f.name)) for f in dataclasses.fields(value)
                  if (name, f.name) not in LATER_FIELDS or getattr(value, f.name) != f.default}  # fmt: skip
        return {'type': type(value).__name__, **fields}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): canon(item) for key, item in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        return sorted(canon(item) for item in value)
    if isinstance(value, (tuple, list)):
        return [canon(item) for item in value]
    return value


def text(value: Any) -> str:
    """The canonical text compared byte for byte."""
    return json.dumps(canon(value), sort_keys=True, separators=(',', ':'))


def digests(planned: dict[str, Any]) -> dict[str, str]:
    """Each plan's canonical text as its SHA-256 (the golden file keeps these: the full plans are ~1.4 MB)."""
    return {key: hashlib.sha256(text(value).encode()).hexdigest() for key, value in planned.items()}


def old_room(pack: Pack, own: frozenset[tuple[int, int, int]], cube: ModuleType) -> dict[str, Any]:
    """The loop's room as `Loop.look` counted it at OLD_COMMIT (macros/loop.py, the lines after "the trade waits
    until both are full"), with `cube`'s `roomed` and `overflow`."""
    rows = cube.roomed(pack).cube or ()
    in_inventory = INVENTORY_CELLS - sum(item.size[0] * item.size[1] for item in pack.items)
    in_cube = sum(row.count('.') for row in rows)
    free = in_inventory + in_cube
    if in_inventory < TRADE_ROOM and cube.overflow(pack, own):
        free = min(free, in_inventory)
    if not any(lines and Grid(lines).has_room(SURE_BLOCK) for lines in (pack.inventory, rows)):
        free = min(free, TRADE_ROOM - 1)
    return {'free': free, 'inventory': in_inventory, 'cube': in_cube, 'rows': list(rows), 'low': free < TRADE_ROOM}


def plans(snapshot: Snapshot, town: ModuleType, cube: ModuleType) -> dict[str, Any]:
    """Every plan the visit's stop makes through `town` and `cube`, canonical. The stash stop's only where the
    snapshot holds the stash view (`start`, `stash`)."""
    pack, own, view = snapshot.pack, snapshot.own, snapshot.view
    loop = cube.loot(pack, own)
    carried = [*loop, *pack.in_cube]
    out: dict[str, Any] = {
        'cube.loot': loop,
        'cube.roomed': cube.roomed(pack),
        'cube.plan': cube.plan(cube.roomed(pack), own),
        'cube.overflow': cube.overflow(pack, own),
        'cube.keys_move': cube.keys_move(pack),
        'cube.keys_move.sure': cube.keys_move(pack, cube.SURE_BLOCK),
        'town.surplus': town.surplus(carried, view if view is not None else snapshot.full),
        'loop.room': old_room(pack, own, cube),
    }
    if view is not None:
        holdings = town.Holdings(pack, own, snapshot.junk, snapshot.unknown)
        deposit = town.deposit_to(snapshot.gold, snapshot.cap)
        stop = town.stash_stop(holdings, view, snapshot.needs, deposit_to=deposit)
        unparked = town.stash_stop(holdings, view, snapshot.needs, park=False)
        out |= {
            'town.stash_stop': stop,
            'town.stash_stop.pages': stop.pages(),
            'town.stash_stop.idle': stop.idle,
            'town.stash_stop.unparked': unparked,
            'town.after': town.after(pack, stop),
            'town.after.unparked': town.after(pack, unparked),
            'town.place': town.place(view.pages, carried),
            'town.out_now': town.out_now(pack.inventory, pack.in_cube),
            'town.rune_transmutes': town.rune_transmutes(dict(view.stacks)),
            'town.uncubed': town.uncubed(dict(view.stacks)),
            'town.unread_way_for_cube': [
                town.unread_way_for_cube(pack, keeper, snapshot.junk, snapshot.needs.block)
                for keeper in pack.in_cube
                if keeper.unit_id not in snapshot.junk
            ],
        }
    return canon(out)


def visit_files() -> list[Path]:
    """Every recorded visit on this host (runs/ is git-ignored), oldest session first."""
    return sorted(RUNS.glob('*/visits/*.json')) if RUNS.is_dir() else []


def stops(paths: list[Path]) -> Iterator[tuple[str, Snapshot]]:
    """Each file's snapshots, named `<file>#<index>:<stop>`."""
    for path in paths:
        for index, snapshot in enumerate(load(path)):
            yield f'{path.name}#{index}:{snapshot.stop}', snapshot


def _git(path: str) -> str | None:
    try:
        done = subprocess.run(
            ['git', 'show', f'{OLD_COMMIT}:{path}'], cwd=ROOT, capture_output=True, text=True, check=False, timeout=30
        )
    except OSError, subprocess.SubprocessError:
        return None
    return done.stdout if done.returncode == 0 else None


def _module(name: str, source: str, renames: dict[str, str]) -> ModuleType:
    for old, new in renames.items():
        source = source.replace(f'from {old} import', f'from {new} import')
    module = ModuleType(name)
    module.__file__ = str(ROOT / 'inventory_tracking' / 'macros' / f'{name.rsplit(".", 1)[-1]}.py')
    sys.modules[name] = module
    exec(compile(source, f'{OLD_COMMIT}:{name}', 'exec'), module.__dict__)  # the repo's own history, read by git
    return module


def old_modules() -> tuple[ModuleType, ModuleType] | None:
    """`(town, cube)` as at OLD_COMMIT (each importing the other old modules, never the moved code); None when git or
    the commit is not there, or the old code no longer imports."""
    sources = {name: _git(f'inventory_tracking/macros/{name}.py') for name in ('cube', 'stash', 'town')}
    if any(source is None for source in sources.values()):
        return None
    names = {name: f'_m3_old_{name}' for name in sources}
    renames = {f'inventory_tracking.macros.{name}': names[name] for name in sources}
    try:
        cube = sys.modules.get(names['cube']) or _module(names['cube'], sources['cube'] or '', renames)
        if names['stash'] not in sys.modules:
            _module(names['stash'], sources['stash'] or '', renames)
        town = sys.modules.get(names['town']) or _module(names['town'], sources['town'] or '', renames)
    except Exception:  # an import the old code needs is gone
        for name in names.values():
            sys.modules.pop(name, None)
        return None
    return town, cube


def write(paths: list[Path] | None = None) -> None:
    """The golden plans of the fixtures, from the code as it is now (run only with the code of OLD_COMMIT)."""
    from inventory_tracking.macros import cube, town

    files = sorted(p for p in FIXTURES.glob('*.json') if p != GOLDEN) if paths is None else paths
    golden = {name: digests(plans(snapshot, town, cube)) for name, snapshot in stops(files)}
    GOLDEN.write_text(json.dumps(golden, sort_keys=True, indent=1) + '\n')
