"""SQLite store for the item collection.

One capture is authoritative for the container keys it lists: placements open in
those containers that the capture no longer shows are closed with `gone_at`;
everything else is left untouched. Shared stash rows are owned by 'shared' and are
refreshed by whichever character captured them last.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from inventory_tracking.collection.models import (
    CaptureRun,
    CaptureSummary,
    Character,
    ContainerSpace,
    ItemRecord,
    Location,
    Placement,
    Sighting,
)


SCHEMA_VERSION = 3
DEFAULT_DATABASE = Path('inventory_tracking/runs/collection/collection.sqlite')

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    name TEXT PRIMARY KEY,
    class_id INTEGER,
    class_name TEXT,
    level INTEGER,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    fingerprint TEXT PRIMARY KEY,
    base_code TEXT NOT NULL,
    base_name TEXT NOT NULL,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    identified INTEGER,
    ethereal INTEGER,
    sockets INTEGER,
    socket_contents TEXT,
    socket_items TEXT NOT NULL,
    runeword TEXT,
    set_name TEXT,
    stat_lines TEXT NOT NULL,
    unresolved INTEGER NOT NULL,
    quantity INTEGER,
    width INTEGER,
    height INTEGER,
    search_text TEXT NOT NULL,
    observation TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS placements (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES items(fingerprint),
    owner TEXT NOT NULL,
    container TEXT NOT NULL,
    tab INTEGER,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    capture_id TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    gone_at TEXT
);
CREATE INDEX IF NOT EXISTS placements_open ON placements(owner, container, tab) WHERE gone_at IS NULL;
CREATE TABLE IF NOT EXISTS spaces (
    owner TEXT NOT NULL,
    container TEXT NOT NULL,
    tab INTEGER,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    free INTEGER NOT NULL,
    occupied INTEGER NOT NULL,
    rows TEXT NOT NULL,
    fits TEXT NOT NULL,
    capture_id TEXT NOT NULL,
    seen_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS spaces_key ON spaces(owner, container, IFNULL(tab, -1));
CREATE TABLE IF NOT EXISTS captures (
    id TEXT PRIMARY KEY,
    character TEXT NOT NULL,
    containers TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    item_count INTEGER NOT NULL
);
"""

PlacementKey = tuple[str, str, str, int | None, int, int]  # fingerprint + location fields


def _placement_key(fingerprint: str, location: Location) -> PlacementKey:
    return fingerprint, location.owner, location.container, location.tab, location.x, location.y


def _row_placement(row: sqlite3.Row) -> Placement:
    return Placement(
        id=row['id'],
        fingerprint=row['fingerprint'],
        location=Location(owner=row['owner'], container=row['container'], tab=row['tab'], x=row['x'], y=row['y']),
        capture_id=row['capture_id'],
        seen_at=row['seen_at'],
        gone_at=row['gone_at'],
    )


def _row_item(row: sqlite3.Row) -> ItemRecord:
    return ItemRecord(
        fingerprint=row['fingerprint'],
        base_code=row['base_code'],
        base_name=row['base_name'],
        name=row['name'],
        rarity=row['rarity'],
        identified=None if row['identified'] is None else bool(row['identified']),
        ethereal=None if row['ethereal'] is None else bool(row['ethereal']),
        sockets=row['sockets'],
        socket_contents=row['socket_contents'],
        socket_items=json.loads(row['socket_items']),
        runeword=row['runeword'],
        set_name=row['set_name'],
        stat_lines=json.loads(row['stat_lines']),
        unresolved=row['unresolved'],
        quantity=row['quantity'],
        width=row['width'],
        height=row['height'],
        observation=json.loads(row['observation']),
    )


class CollectionStore:
    def __init__(self, path: Path | str = DEFAULT_DATABASE):
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def open(self) -> CollectionStore:
        if self.path != Path(':memory:'):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, 2, SCHEMA_VERSION):
            connection.close()
            raise ValueError(f'Unsupported collection schema version {version}')
        connection.executescript(SCHEMA)
        # Columns added after version 1 (quantity, 2026-09-25) and 2 (width/height, 2026-09-25);
        # the spaces table comes from the script above. Idempotent by column presence.
        present = {row['name'] for row in connection.execute('PRAGMA table_info(items)')}
        for column in ('quantity', 'width', 'height'):
            if column not in present:
                connection.execute(f'ALTER TABLE items ADD COLUMN {column} INTEGER')
        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        self.connection = connection
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> CollectionStore:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def db(self) -> sqlite3.Connection:
        if self.connection is None:
            raise ValueError('Collection store is not open')
        return self.connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        db = self.db
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
        except BaseException:
            db.execute('ROLLBACK')
            raise
        db.execute('COMMIT')

    # --- writes -------------------------------------------------------------------

    def record_capture(
        self, capture: CaptureRun, sightings: list[Sighting], spaces: list[ContainerSpace] | None = None
    ) -> CaptureSummary:
        """Apply one full capture atomically; see the module docstring for the closure rule."""
        authoritative = set(capture.containers)
        for space in spaces or []:
            if space.key not in authoritative:
                raise ValueError(f'Space outside captured containers: {space.key}')
        for sighting in sightings:
            if sighting.location.key not in authoritative:
                raise ValueError(f'Sighting outside captured containers: {sighting.location.label}')
        seen_at = capture.started_at
        with self.transaction() as db:
            self._upsert_character(db, capture.character, seen_at)
            for sighting in sightings:
                self._upsert_item(db, sighting.item, seen_at)
            existing: dict[PlacementKey, int] = {}
            for key in authoritative:
                for row in db.execute(
                    'SELECT * FROM placements WHERE owner = ? AND container = ? AND tab IS ? AND gone_at IS NULL',
                    key,
                ):
                    placement = _row_placement(row)
                    existing[_placement_key(placement.fingerprint, placement.location)] = placement.id or 0
            current = {_placement_key(s.item.fingerprint, s.location): s for s in sightings}
            gone_keys = set(existing) - set(current)
            new_keys = set(current) - set(existing)
            for key in gone_keys:
                db.execute('UPDATE placements SET gone_at = ? WHERE id = ?', (seen_at, existing[key]))
            gone_fingerprints = {key[0] for key in gone_keys}
            moved = 0
            for key in new_keys:
                sighting = current[key]
                if sighting.item.fingerprint in gone_fingerprints:
                    moved += 1
                location = sighting.location
                db.execute(
                    'INSERT INTO placements (fingerprint, owner, container, tab, x, y, capture_id, seen_at) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        sighting.item.fingerprint,
                        location.owner,
                        location.container,
                        location.tab,
                        location.x,
                        location.y,
                        capture.id,
                        seen_at,
                    ),
                )
            for space in spaces or []:
                db.execute(
                    'INSERT INTO spaces (owner, container, tab, width, height, free, occupied, rows, fits, capture_id, '
                    'seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'ON CONFLICT(owner, container, IFNULL(tab, -1)) DO UPDATE SET width = excluded.width, '
                    'height = excluded.height, free = excluded.free, occupied = excluded.occupied, '
                    'rows = excluded.rows, fits = excluded.fits, capture_id = excluded.capture_id, '
                    'seen_at = excluded.seen_at',
                    (
                        space.owner,
                        space.container,
                        space.tab,
                        space.width,
                        space.height,
                        space.free,
                        space.occupied,
                        json.dumps(space.rows),
                        json.dumps(space.fits),
                        capture.id,
                        seen_at,
                    ),
                )
            db.execute(
                'INSERT OR REPLACE INTO captures '
                '(id, character, containers, started_at, finished_at, status, item_count) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    capture.id,
                    capture.character.name,
                    json.dumps([list(key) for key in capture.containers]),
                    capture.started_at,
                    seen_at,
                    'complete',
                    len(sightings),
                ),
            )
        return CaptureSummary(
            total=len(sightings),
            new=len(new_keys) - moved,
            moved=moved,
            unchanged=len(set(existing) & set(current)),
            gone=len(gone_keys) - moved,
        )

    @staticmethod
    def _upsert_character(db: sqlite3.Connection, character: Character, seen_at: str) -> None:
        db.execute(
            'INSERT INTO characters (name, class_id, class_name, level, first_seen, last_seen) '
            'VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET '
            'class_id = COALESCE(excluded.class_id, class_id), '
            'class_name = COALESCE(excluded.class_name, class_name), '
            'level = COALESCE(excluded.level, level), last_seen = excluded.last_seen',
            (character.name, character.class_id, character.class_name, character.level, seen_at, seen_at),
        )

    @staticmethod
    def _upsert_item(db: sqlite3.Connection, item: ItemRecord, seen_at: str) -> None:
        db.execute(
            'INSERT INTO items (fingerprint, base_code, base_name, name, rarity, identified, ethereal, sockets, '
            'socket_contents, socket_items, runeword, set_name, stat_lines, unresolved, quantity, width, height, '
            'search_text, observation, first_seen, last_seen) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'ON CONFLICT(fingerprint) DO UPDATE SET last_seen = excluded.last_seen, '
            'stat_lines = excluded.stat_lines, quantity = excluded.quantity, '
            'width = COALESCE(excluded.width, width), height = COALESCE(excluded.height, height), '
            'search_text = excluded.search_text, observation = excluded.observation',
            (
                item.fingerprint,
                item.base_code,
                item.base_name,
                item.name,
                item.rarity,
                item.identified,
                item.ethereal,
                item.sockets,
                item.socket_contents,
                json.dumps(item.socket_items),
                item.runeword,
                item.set_name,
                json.dumps(item.stat_lines),
                item.unresolved,
                item.quantity,
                item.width,
                item.height,
                item.search_text,
                json.dumps(item.observation, sort_keys=True),
                seen_at,
                seen_at,
            ),
        )

    # --- reads --------------------------------------------------------------------

    def characters(self) -> list[Character]:
        return [
            Character(name=r['name'], class_id=r['class_id'], class_name=r['class_name'], level=r['level'])
            for r in self.db.execute('SELECT * FROM characters ORDER BY name')
        ]

    def item(self, fingerprint: str) -> ItemRecord | None:
        row = self.db.execute('SELECT * FROM items WHERE fingerprint = ?', (fingerprint,)).fetchone()
        return _row_item(row) if row else None

    def placements(self, fingerprint: str, *, include_gone: bool = False) -> list[Placement]:
        clause = '' if include_gone else ' AND gone_at IS NULL'
        rows = self.db.execute(f'SELECT * FROM placements WHERE fingerprint = ?{clause} ORDER BY id', (fingerprint,))
        return [_row_placement(r) for r in rows]

    def query(
        self,
        text: str | None = None,
        *,
        owner: str | None = None,
        container: str | None = None,
        sockets: int | str | None = None,
    ) -> list[tuple[ItemRecord, Placement]]:
        """Open placements whose item matches every word of `text` and the filters."""
        sql = 'SELECT p.*, i.* FROM placements p JOIN items i ON i.fingerprint = p.fingerprint WHERE p.gone_at IS NULL'
        params: list[Any] = []
        for word in (text or '').lower().split():
            sql += " AND i.search_text LIKE ? ESCAPE '\\'"
            params.append('%' + word.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
        if owner is not None:
            sql += ' AND p.owner = ?'
            params.append(owner)
        if container is not None:
            sql += ' AND p.container = ?'
            params.append(container)
        if sockets == 'empty':
            sql += " AND i.sockets > 0 AND i.socket_contents = 'empty'"
        elif sockets is not None:
            sql += ' AND i.sockets = ?'
            params.append(int(sockets))
        sql += ' ORDER BY i.name, p.owner, p.container, p.tab, p.y, p.x'
        return [(_row_item(r), _row_placement(r)) for r in self.db.execute(sql, params)]

    def spaces(self, *, fits: str | None = None) -> list[ContainerSpace]:
        """Every known grid, optionally only those where at least one item of size `fits` ('2x4') still fits."""
        result = []
        for row in self.db.execute('SELECT * FROM spaces ORDER BY owner, container, tab'):
            space = ContainerSpace(
                owner=row['owner'],
                container=row['container'],
                tab=row['tab'],
                width=row['width'],
                height=row['height'],
                free=row['free'],
                occupied=row['occupied'],
                rows=json.loads(row['rows']),
                fits=json.loads(row['fits']),
            )
            if fits is None or space.fits.get(fits, 0) > 0:
                result.append(space)
        return result

    def counts(self) -> dict[str, int]:
        db = self.db
        return {
            'characters': db.execute('SELECT COUNT(*) FROM characters').fetchone()[0],
            'items': db.execute('SELECT COUNT(*) FROM items').fetchone()[0],
            'placements': db.execute('SELECT COUNT(*) FROM placements WHERE gone_at IS NULL').fetchone()[0],
            'gone': db.execute('SELECT COUNT(*) FROM placements WHERE gone_at IS NOT NULL').fetchone()[0],
            'captures': db.execute('SELECT COUNT(*) FROM captures').fetchone()[0],
        }
