"""The town visit's snapshots (rca/2026-10-18/arch-town-planning.md §4): what a visit holds at its start and after
each stop, as JSON beside the service's probe.log (`visits/<HHMMSS>.json`), and the codec reading them back for offline
replay (townplan.py `plan_visit`) and test fixtures. No game reads of its own; never raises into the visit.

The file: `{"version": 1, "visit": "<HHMMSS>", "stops": [<snapshot>, ...]}`, stops `start` (after Cain and the
verdicts), `stash` (before any transmute), `shops` (after Jamella and Halbu), `end` (with the contract's misses). The
stash view is in `start` and `stash` only; the plan's predicted misses in `start`. An item is
`[unit, class, x, y, across, down, quality, identified, unique]`.
"""

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, Page, StashView
from inventory_tracking.macros.portal import FROM_SLING, FROM_TOME, PortalSource
from inventory_tracking.macros.town import Cell, Exit, Needs


__all__ = [
    'FOLDER',
    'VERSION',
    'Recorder',
    'Snapshot',
    'carried_from',
    'carried_json',
    'load',
    'pack_from',
    'pack_json',
    'session_directory',
    'snapshot_from',
    'snapshot_json',
    'view_from',
    'view_json',
]

VERSION = 1
FOLDER = 'visits'  # beside probe.log: runs/alt-d/<service>/visits/<HHMMSS>.json


@dataclass(frozen=True)
class Snapshot:
    """What a visit holds at one stop: enough for `townplan.plan_visit` to replay it."""

    stop: str
    pack: Pack
    own: frozenset[Cell]
    needs: Needs
    exit: Exit
    view: StashView | None = None
    junk: frozenset[int] = frozenset()
    unknown: frozenset[int] = frozenset()
    full: frozenset[int] = frozenset()
    gold: int | None = None
    cap: int | None = None
    at: str = ''  # the wall clock, HH:MM:SS
    misses: tuple[str, ...] = ()  # the contract's (`end`)
    predicted: tuple[str, ...] | None = None  # the plan's (`start`), None not planned


# The codec


def carried_json(item: Carried) -> list[int | bool]:
    return [item.unit_id, item.txt, item.x, item.y, *item.size, item.quality, item.identified, item.unique]


def carried_from(raw: Sequence[Any]) -> Carried:
    unit, txt, x, y, across, down, quality, identified, unique = raw
    return Carried(int(unit), int(txt), int(x), int(y), (int(across), int(down)), int(quality), bool(identified),
                   int(unique))  # fmt: skip


def _items(raw: Sequence[Any]) -> tuple[Carried, ...]:
    return tuple(carried_from(item) for item in raw)


def _rows(raw: Sequence[str] | None) -> tuple[str, ...] | None:
    return tuple(raw) if raw is not None else None


def pack_json(pack: Pack) -> dict[str, Any]:
    return {
        'items': [carried_json(i) for i in pack.items],
        'cube': list(pack.cube) if pack.cube is not None else None,
        'cube_items': sorted(pack.cube_items),
        'in_cube': [carried_json(i) for i in pack.in_cube],
        'keys': pack.keys,
        'portals': pack.portals,
        'key_room': pack.key_room,
        'pointer': pack.pointer,
        'identifies': pack.identifies,
        'stashed': [carried_json(i) for i in pack.stashed],
        'stash': list(pack.stash) if pack.stash is not None else None,
    }


def pack_from(raw: dict[str, Any]) -> Pack:
    return Pack(
        _items(raw['items']),
        _rows(raw.get('cube')),
        frozenset(raw.get('cube_items', ())),
        _items(raw.get('in_cube', ())),
        keys=raw.get('keys'),
        portals=raw.get('portals'),
        key_room=raw.get('key_room'),
        pointer=raw.get('pointer'),
        identifies=raw.get('identifies'),
        stashed=_items(raw.get('stashed', ())),
        stash=_rows(raw.get('stash')),
    )


def _page_json(page: Page) -> dict[str, Any]:
    return {
        'index': page.index,
        'rows': list(page.rows),
        'owner': page.owner,
        'units': sorted(page.units),
        'items': [carried_json(i) for i in page.items],
    }


def _page_from(raw: dict[str, Any]) -> Page:
    return Page(int(raw['index']), tuple(raw['rows']), raw.get('owner'), frozenset(raw.get('units', ())),
                _items(raw.get('items', ())))  # fmt: skip


def view_json(view: StashView) -> dict[str, Any]:
    return {'pages': [_page_json(p) for p in view.pages], 'stacks': [list(s) for s in view.stacks]}


def view_from(raw: dict[str, Any]) -> StashView:
    return StashView(
        tuple(_page_from(p) for p in raw['pages']), tuple((int(txt), int(n)) for txt, n in raw.get('stacks', ()))
    )


def _needs_json(needs: Needs) -> dict[str, Any]:
    source = needs.portals
    return {
        'block': list(needs.block),
        'keys': needs.keys,
        'portals': {'skill': source.skill, 'name': source.name, 'stocked': source.stocked},
        'identifies': needs.identifies,
        'stack_room': needs.stack_room,
    }


def _needs_from(raw: dict[str, Any]) -> Needs:
    given = raw['portals']
    source = PortalSource(int(given['skill']), str(given['name']), bool(given['stocked']))
    source = next((known for known in (FROM_TOME, FROM_SLING) if known == source), source)
    block = raw['block']
    return Needs((int(block[0]), int(block[1])), int(raw['keys']), source, int(raw['identifies']),
                 int(raw['stack_room']))  # fmt: skip


def snapshot_json(snapshot: Snapshot) -> dict[str, Any]:
    return {
        'stop': snapshot.stop,
        'at': snapshot.at,
        'pack': pack_json(snapshot.pack),
        'view': view_json(snapshot.view) if snapshot.view is not None else None,
        'own': sorted(list(cell) for cell in snapshot.own),
        'junk': sorted(snapshot.junk),
        'unknown': sorted(snapshot.unknown),
        'full': sorted(snapshot.full),
        'gold': snapshot.gold,
        'cap': snapshot.cap,
        'needs': _needs_json(snapshot.needs),
        'exit': snapshot.exit.value,
        'misses': list(snapshot.misses),
        'predicted': list(snapshot.predicted) if snapshot.predicted is not None else None,
    }


def snapshot_from(raw: dict[str, Any]) -> Snapshot:
    predicted = raw.get('predicted')
    return Snapshot(
        stop=str(raw['stop']),
        pack=pack_from(raw['pack']),
        own=frozenset((int(txt), int(x), int(y)) for txt, x, y in raw['own']),
        needs=_needs_from(raw['needs']),
        exit=Exit(raw['exit']),
        view=view_from(raw['view']) if raw.get('view') is not None else None,
        junk=frozenset(raw.get('junk', ())),
        unknown=frozenset(raw.get('unknown', ())),
        full=frozenset(raw.get('full', ())),
        gold=raw.get('gold'),
        cap=raw.get('cap'),
        at=str(raw.get('at', '')),
        misses=tuple(raw.get('misses', ())),
        predicted=tuple(predicted) if predicted is not None else None,
    )


def load(path: Path) -> tuple[Snapshot, ...]:
    """A visit file's snapshots, in their order."""
    return tuple(snapshot_from(stop) for stop in json.loads(path.read_text())['stops'])


# The writer


def session_directory() -> Path | None:
    """The service's run directory (where probe.log is written), None outside the service."""
    try:
        for handler in tuple(LOG.handlers):
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).name == 'probe.log':
                return Path(handler.baseFilename).parent
    except Exception as error:  # never into the visit
        LOG.info('Macro: visit snapshot: no run directory: %s', error)
    return None


@dataclass
class Recorder:
    """One visit's file, rewritten on each `note` (a visit cut short keeps what it had). `directory` None: nothing is
    written. Never raises: a failure is logged once, then it stops. `view`, `coins`, `cap`: as read at the stash."""

    directory: Path | None = field(default_factory=session_directory)
    clock: Callable[[], datetime] = datetime.now
    stops: list[dict[str, Any]] = field(default_factory=list)
    path: Path | None = None
    failed: bool = False
    view: StashView | None = None
    coins: int | None = None
    cap: int | None = None

    @property
    def active(self) -> bool:
        return self.directory is not None and not self.failed

    def note(self, snapshot: Snapshot) -> None:
        if not self.active:
            return
        try:
            now = self.clock()
            if not snapshot.at:
                snapshot = replace(snapshot, at=now.strftime('%H:%M:%S'))
            if snapshot.gold is None and snapshot.cap is None:
                snapshot = replace(snapshot, gold=self.coins, cap=self.cap)
            self.stops.append(snapshot_json(snapshot))
            if self.path is None:
                assert self.directory is not None
                folder = self.directory / FOLDER
                folder.mkdir(parents=True, exist_ok=True)
                stamp, n = now.strftime('%H%M%S'), 1
                self.path = folder / f'{stamp}.json'
                while self.path.exists():
                    n += 1
                    self.path = folder / f'{stamp}-{n}.json'
            self._write()
        except Exception as error:  # never into the visit
            self.failed = True
            LOG.info('Macro: visit snapshot: not written: %s', error)

    def gold(self, coins: int | None, cap: int | None) -> None:
        """The gold and its cap as the stash stop read them, for the snapshots before and after."""
        self.coins, self.cap = coins, cap
        for stop in self.stops:
            if stop.get('gold') is None:
                stop['gold'], stop['cap'] = coins, cap

    def _write(self) -> None:
        assert self.path is not None
        visit = self.path.stem
        self.path.write_text(json.dumps({'version': VERSION, 'visit': visit, 'stops': self.stops},
                                        separators=(',', ':')))  # fmt: skip
