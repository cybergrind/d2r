"""Every monster dot of the level map, read by the canvas itself (rca/2026-10-14/run-1916-hud-findings.md §2).

The player, 2026-10-14: "monsters on the map appear with a big, visible delay". The dots came with the level card,
rebuilt every 2 s while the macro works (rca/2026-10-13/latency-findings.md fix 1, which slowed the card and the
probe to keep the service's reads off the macro's GIL): memory to drawn 1.95 s median, a dead monster's dot 2.10 s
after its death. The canvas is a process of its own, with its own GIL, so its reads cost the macro nothing; this
module gives it the dots between cards without the service doing any more:

- **Each frame** (`LiveDots.frame`): every dot carries its unit record's address and id (terror/tracker.py
  `map_dots`); the canvas reads each record's id, mode and path pointer, then the path's position. A dead mode drops
  the dot at once; a record freed or reused (another id, not a monster) leaves the dot where it was last read, as the
  tracker keeps it, unless the client would hold the monster there (within HELD_RANGE of the player: it is gone).
  The reads are batched: one `process_vm_readv` per batch where the kernel allows it, else one `pread` each; at most
  MAX_FOLLOWED dots, the nearest the player (the rest stand as published).
- **Every WALK_SECONDS** (`LiveDots._walk`): the canvas walks the game's monster table itself (terror/monsters.py
  `monster_units`, the probe's own walk; findings fix 3) for the hostiles the card has no dot for yet, judged by the
  tracker's own predicates (terror/tracker.py `counted`, `leading`: allies, siege works and scenery are never dots).
  They are drawn as plain or leader dots (the danger bands come with the next card) and followed each frame.

`DotStats` measures it: once a minute while dots are drawn, hud.log says how many dots were new, which reader saw
them first, how much later the card brought them, how soon a death was drawn, and what the reads and draws cost
(the `HUD: dots:` line).
"""

import math
import os
import statistics
import struct
import time

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import MONSTER_UNIT
from inventory_tracking.hud.live import LiveMemory
from inventory_tracking.native.layout import DEAD_MODES, TILE_UNITS
from inventory_tracking.native.memory import open_memory, vm_call, vm_read_spans
from inventory_tracking.terror.monsters import monster_units
from inventory_tracking.terror.tracker import HELD_RANGE, counted, leading


UNIT_RECORD = 0x40  # bytes of a unit record read per dot: its type +0x00, id +0x08, mode +0x0C, path pointer +0x38
UNIT_ID, UNIT_MODE, UNIT_PATH = 0x08, 0x0C, 0x38  # native/units.py `walk_units`
PATH_BYTES = 8  # +0x00..+0x08 of the dynamic path: the position (hud/live.py `position`)
HELD_TILES = HELD_RANGE / TILE_UNITS  # a freed record this near the player is a monster gone, not out of range
MAX_FOLLOWED = 128  # dots read per frame, the nearest the player; a level holds 20-150 alive around the character
MAX_DRIFT = 40  # tiles from the published position; further means the address is stale (hud/live.py)
WALK_SECONDS = 0.2  # between the canvas's own walks of the monster table: a new monster drawn ~0.1 s after it is held
STATS_SECONDS = 60.0  # between the `HUD: dots:` lines


VM_CALL = vm_call()  # None where libc has no process_vm_readv


class LiveDots(LiveMemory):
    """The canvas's reader of the map's monsters (module text). `open_memory(pid)` -> fd, `read(fd, size, address)`
    a pread; `call` libc's process_vm_readv (None: pread only); `walk(read, table, known)` the probe's walk."""

    def __init__(
        self,
        open_memory=open_memory,
        read=os.pread,
        call=VM_CALL,
        walk=monster_units,
        stats=None,
    ):
        super().__init__(open_memory, read)
        self.call, self.walk = call, walk
        self.stats = stats if stats is not None else DotStats()
        self.reset()

    def reset(self):
        self.last: dict[int, tuple[float, float]] = {}  # unit id -> (x, y) tiles as last read alive
        self.kinds: dict[int, str | None] = {}  # unit id -> 'mob' / 'leader' as first read; None: no dot (an ally)
        self.extra: dict[int, list] = {}  # unit id -> map row: hostiles held that the card has no dot for yet
        self.walked = -math.inf
        self.area: int | None = None

    def attach(self, pid) -> bool:
        if pid != self.pid:
            self.reset()  # another game: nothing read of the last one holds
        return super().attach(pid)

    def spans(self, spans) -> list[bytes | None]:
        """The bytes of each (address, size), None where unreadable: one batched call, or a pread each."""
        assert self.pid is not None
        assert self.fd is not None
        if self.call is not None:
            found = vm_read_spans(self.call, self.pid, spans)
            if found is not None:
                return found
            LOG.info('HUD: process_vm_readv refused; the dots are read one pread each')
            self.call = None
        out: list[bytes | None] = []
        for address, size in spans:
            try:
                data = self.read(self.fd, size, address) if address else None
            except OSError:
                data = None
            out.append(data if data is not None and len(data) == size else None)
        return out

    def exact(self, address: int, size: int) -> bytes:
        """One read for the walk (terror/monsters.py's `read`): the bytes, or OSError."""
        assert self.fd is not None
        data = self.read(self.fd, size, address)
        if len(data) != size:
            raise OSError('short read')
        return data

    def frame(self, card: dict | None, ground: dict | None, now: float) -> dict | None:
        """Where the player and each monster dot of the map card (`card`, its 'map' dict) and of the ground marks
        (`ground`) are now: {'player': [x, y] or None, 'dots': {unit id: [x, y] or None (gone)}, 'extra': [map rows
        of hostiles the card has no dot for]}. None when there is nothing to read."""
        live = (card or {}).get('live') or (ground or {}).get('live')
        if not live or not self.attach(live[0]):
            return None
        started = time.perf_counter()
        published = (card or ground or {}).get('player') or (0.0, 0.0)
        dots = {row[6]: (row[5], row[2], row[3]) for row in (card or {}).get('pois', ()) if len(row) >= 7 and row[5]}
        for row in (ground or {}).get('marks', ()):
            if len(row) >= 6 and row[4]:
                dots.setdefault(row[5], (row[4], row[1], row[2]))
        units = (card or {}).get('units')
        if units and units[1] != self.area:
            self.extra, self.last, self.area = {}, {}, units[1]
        if units and now - self.walked >= WALK_SECONDS:
            self._walk(units[0], units[1], set(dots), now)
        for uid in [uid for uid in self.extra if uid in dots]:
            del self.extra[uid]  # the card has it now
        followed = {**dots, **{uid: (row[5], row[2], row[3]) for uid, row in self.extra.items()}}
        player = self._player(live[1], published)
        near = player or published
        chosen = sorted(followed.items(), key=lambda item: math.dist(near, item[1][1:]))[:MAX_FOLLOWED]
        found = self._read(chosen, near)
        extra = []
        for uid, row in list(self.extra.items()):
            where = found.get(uid, row[2:4])  # one not read this frame (past MAX_FOLLOWED) stands as walked
            if where is None:
                del self.extra[uid]  # dead, or gone: the next walk says whether it is back
            else:
                extra.append([*row[:2], *where, *row[4:]])
        self.stats.framed(now, dots, found, self.extra, 1000 * (time.perf_counter() - started), len(chosen))
        return {'player': list(player) if player else None, 'dots': found, 'extra': extra}

    def _player(self, address: int, published) -> tuple[float, float] | None:
        data = self.spans([(address, PATH_BYTES)])[0]
        if data is None:
            return None
        x, y = position(data)
        return (x, y) if abs(x - published[0]) <= MAX_DRIFT and abs(y - published[1]) <= MAX_DRIFT else None

    def _read(self, chosen, near) -> dict[int, list | None]:
        """{unit id: [x, y] now, or None: dead, or gone where the client would hold it} for `chosen`."""
        records = self.spans([(unit, UNIT_RECORD) for _, (unit, _, _) in chosen])
        alive, found = [], {}
        for (uid, (_, x, y)), record in zip(chosen, records, strict=True):
            kind, unit_id, mode = struct.unpack_from('<IxxxxII', record) if record else (None, None, None)
            path = struct.unpack_from('<Q', record, UNIT_PATH)[0] if record else 0
            if kind != MONSTER_UNIT or unit_id != uid or not path:  # freed, or the memory is another unit's now
                last = self.last.get(uid, (x, y))
                found[uid] = None if math.dist(last, near) <= HELD_TILES else list(last)
            elif mode in DEAD_MODES:
                found[uid] = None
                self.last.pop(uid, None)
            else:
                alive.append((uid, x, y, path))
        for (uid, x, y, _), data in zip(alive, self.spans([(path, PATH_BYTES) for *_, path in alive]), strict=True):
            now = position(data) if data is not None else None
            if now is None or abs(now[0] - x) > MAX_DRIFT or abs(now[1] - y) > MAX_DRIFT:
                now = self.last.get(uid, (x, y))
            self.last[uid] = now
            found[uid] = list(now)
        return found

    def _walk(self, table: int, area: int, shown: set[int], now: float) -> None:
        """The hostiles of `area` held now that the card has no dot for (`shown`): `extra`."""
        started = time.perf_counter()
        self.walked = now
        try:
            monsters, _ = self.walk(self.exact, table, known={uid for uid, kind in self.kinds.items()})
        except OSError, ValueError, struct.error:
            return
        extra = {}
        for monster in monsters:
            uid = monster.unit_id
            if uid not in self.kinds and monster.stats is not None:  # its first sight read: is it a dot at all?
                sighting = {'txt_id': monster.txt_id, 'stats': monster.stats, 'data_hex': monster.data_hex}
                self.kinds[uid] = ('leader' if leading(sighting) else 'mob') if counted(sighting) else None
            kind = self.kinds.get(uid)
            if kind is None or uid in shown or monster.mode in DEAD_MODES or not (monster.x or monster.y):
                continue
            if monster.area not in (None, area):
                continue
            label = 'unique' if kind == 'leader' else 'monster'
            x, y = monster.x / TILE_UNITS, monster.y / TILE_UNITS
            extra[uid] = [label, kind, x, y, monster.path_at, monster.unit_at, uid]
        self.extra = extra
        self.stats.walked(now, 1000 * (time.perf_counter() - started), extra)


def position(data: bytes) -> tuple[float, float]:
    """Path bytes +0x00..+0x08 -> (x, y) in tiles (hud/live.py `position`)."""
    x_fraction, x, y_fraction, y = struct.unpack('<HHHH', data)
    return (x + x_fraction / 65536) / TILE_UNITS, (y + y_fraction / 65536) / TILE_UNITS


def quantiles(values) -> tuple[float, float]:
    """(median, p90) of `values`."""
    ordered = sorted(values)
    return statistics.median(ordered), ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]


class DotStats:
    """The `HUD: dots:` line (module text): per unit id, when the canvas first had it and from which reader, when it
    was first painted, when the card brought a dot the walk had first, when the frame read a death and when the card
    dropped that dot; and what the frame reads, the walks and the draws cost."""

    def __init__(self, every: float = STATS_SECONDS, log=LOG.info):
        self.every, self.log = every, log
        self.first: dict[int, tuple[float, str]] = {}  # unit id -> (when first had, 'walk' or 'card')
        self.unpainted: dict[int, float] = {}  # unit id -> when first had, not painted yet
        self.died: dict[int, float] = {}  # unit id -> when the frame read it dead, while the card still has it
        self.brought: set[int] = set()  # unit ids the walk had first and the card has brought since
        self.reset(-math.inf)

    def reset(self, now: float) -> None:
        self.since = now
        self.new = {'walk': 0, 'card': 0}
        self.painted: list[float] = []  # s from first had to painted
        self.card_later: list[float] = []  # s from the walk's sighting to the card's dot
        self.dead_later: list[float] = []  # s from the frame's death read to the card dropping the dot
        self.deaths = 0
        self.frame_ms: list[float] = []
        self.counts: list[int] = []
        self.walk_ms: list[float] = []
        self.walks: list[float] = []
        self.draw_ms: list[float] = []

    def walked(self, now: float, ms: float, extra: dict) -> None:
        self.walk_ms.append(ms)
        self.walks.append(now)
        for uid in extra:
            self._had(uid, now, 'walk')

    def framed(self, now: float, dots: dict, found: dict, extra: dict, ms: float, count: int) -> None:
        if self.since == -math.inf:
            self.since = now
        self.frame_ms.append(ms)
        self.counts.append(count)
        for uid in dots:
            first = self.first.get(uid)
            if first is None:
                self._had(uid, now, 'card')
            elif first[1] == 'walk' and uid not in self.brought:
                self.card_later.append(now - first[0])
                self.brought.add(uid)
            if found.get(uid, ()) is None and uid not in self.died:
                self.died[uid] = now
                self.deaths += 1
        for uid in [uid for uid in self.died if uid not in dots]:
            self.dead_later.append(now - self.died.pop(uid))
        if now - self.since >= self.every:
            self.flush(now)

    def _had(self, uid: int, now: float, by: str) -> None:
        if uid not in self.first:
            self.first[uid] = (now, by)
            self.unpainted[uid] = now
            self.new[by] += 1

    def drew(self, now: float, ms: float) -> None:
        """The canvas painted: every dot had and not painted yet is painted now."""
        self.draw_ms.append(ms)
        self.painted += [now - had for had in self.unpainted.values()]
        self.unpainted.clear()

    def flush(self, now: float) -> None:
        if self.frame_ms and sum(self.new.values()) + self.deaths:
            self.log('HUD: dots: %s', self.line(now))
        if len(self.first) > 4096:  # a long session: the oldest ids are of levels long left
            self.first = dict(list(self.first.items())[-2048:])
            self.brought &= set(self.first)
        self.reset(now)

    def line(self, now: float) -> str:
        def ms(values) -> str:
            if not values:
                return 'n/a'
            median, p90 = quantiles(values)
            return f'{median:.1f} ms median, {p90:.1f} p90'

        def seconds(values) -> str:
            if not values:
                return 'n/a'
            median, p90 = quantiles(values)
            return f'{median:.2f} s median, {p90:.2f} p90'

        span = max(now - self.since, 1e-9)
        gaps = [b - a for a, b in zip(self.walks, self.walks[1:], strict=False)]
        walk = f'walk every {statistics.median(gaps):.2f} s, {ms(self.walk_ms)}' if gaps else 'no walk'
        new = sum(self.new.values())
        return (
            f'{new} new in {span:.0f} s ({self.new["walk"]} first by the walk, {self.new["card"]} by the card), '
            f'had→painted {seconds(self.painted)}; card later than the walk by {seconds(self.card_later)}; '
            f'{self.deaths} deaths read by the frame, card dropped them {seconds(self.dead_later)} later; '
            f'frame read {ms(self.frame_ms)} for {statistics.median(self.counts) if self.counts else 0:.0f} dots; '
            f'{walk}; {len(self.draw_ms) / span:.1f} draws/s, {ms(self.draw_ms)}'
        )
