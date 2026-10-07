"""Terror Zone research probe, polled from `serve`: what the client shows of monsters and kills.

Writes one JSONL event stream per service run (terror-probe.jsonl in the run directory) to
answer, from real games: how far monsters are visible, whether they vanish when their rooms
unload and come back, how many rooms of a level get loaded, and how a Herald looks in memory
(monster data and stats on first sight). Win+C writes a `mark` with the monsters present, so a
Herald on screen can be matched to its `seen` record. No display, no game input.

With a tracker (tracker.py) the same events drive the Terror Zone card: `tick` publishes the
current Herald group's lines while D2R is focused.

Events: area (entered; level Room2 count), rooms (newly loaded Room2s), life (the player's life,
whenever it changed: burst research, terror/bursts.py), around (every second with live monsters
within a screen: their live positions and modes with the player's life and states, the statistics behind
the threat level, terror/exposure.py), seen (first sight, with data/stats), died
(alive -> dead/dying mode: one kill), gone (dropped from the client; alive or not), back
(reappeared), summary (every few seconds), left_game (menu: the ledger resets), mark, and
elite_kill / shard (a pack leader's death, a Worldstone Shard first seen on the ground: terror/shards.py).
"""

import json
import math
import threading
from typing import Any

from inventory_tracking.common import LOG, timestamp
from inventory_tracking.native.layout import DEAD_MODES, TOWN_IDS
from inventory_tracking.terror.monsters import Monster, MonsterSnapshot, observe_monsters


AROUND_REACH = 60  # world units: about a screen, the reach of what can hurt the player now


def distance(monster: Monster, location) -> int:
    return round(math.hypot(monster.x - location.x, monster.y - location.y))


class MonsterLedger:
    def __init__(self, *, summary_seconds=10.0, around_seconds=1.0):
        self.summary_seconds, self.around_seconds = summary_seconds, around_seconds
        self.reset()

    def reset(self):
        self.area: int | None = None
        self.present: dict[int, Monster] = {}
        self.gone: dict[int, Monster] = {}
        self.seen: dict[int, set[int]] = {}  # area -> unit ids
        self.killed: dict[int, int] = {}
        self.rooms: dict[int, set[int]] = {}  # area -> Room2s ever loaded
        self.level_rooms: dict[int, int | None] = {}
        self.next_summary: float | None = None
        self.life: tuple[int, int] | None = None  # the player's life as last logged
        self.next_around = -math.inf

    @property
    def known(self) -> set[int]:
        return set(self.present) | set(self.gone)

    def update(self, snapshot: MonsterSnapshot, now: float) -> list[dict[str, Any]]:
        t = round(now, 3)
        location = snapshot.location
        if location is None:
            if self.area is None:
                return []
            event: dict[str, Any] = {'event': 'left_game', 't': t, 'killed': dict(self.killed)}
            event['seen'] = {area: len(units) for area, units in self.seen.items()}
            self.reset()
            return [event]
        events: list[dict[str, Any]] = []
        here = location.area_id
        if here != self.area:
            self.area = here
            if snapshot.level_rooms is not None or here not in self.level_rooms:
                self.level_rooms[here] = snapshot.level_rooms
            event = {'event': 'area', 't': t, 'area': here, 'level_rooms': self.level_rooms[here]}
            if snapshot.level_hex is not None:
                event['level_hex'] = snapshot.level_hex
            events.append(event)
        if snapshot.player_life is not None and snapshot.player_life != self.life:
            self.life = snapshot.player_life
            position = {'x': location.x, 'y': location.y}
            events.append({'event': 'life', 't': t, 'area': here, 'life': self.life[0], 'max': self.life[1]} | position)
        if snapshot.player_life is not None and here not in TOWN_IDS and now >= self.next_around:
            near = [
                [m.unit_id, m.txt_id, m.mode, m.x, m.y]
                for m in snapshot.monsters
                if m.mode not in DEAD_MODES and m.area in (None, here) and distance(m, location) <= AROUND_REACH
            ]
            if near:  # allies too: the reader tells them apart by their `seen` event
                self.next_around = now + self.around_seconds
                life, most = snapshot.player_life
                events.append(
                    {'event': 'around', 't': t, 'area': here, 'x': location.x, 'y': location.y}
                    | {'life': life, 'max': most, 'near': near}
                    | ({} if snapshot.player_states is None else {'states': sorted(snapshot.player_states)})
                )
        rooms = self.rooms.setdefault(here, set())
        new_rooms = snapshot.room2s - rooms
        if new_rooms:
            rooms |= new_rooms
            events.append(
                {'event': 'rooms', 't': t, 'area': here, 'new': len(new_rooms), 'loaded_ever': len(rooms)}
                | {'bounds': [list(room) for room in sorted(new_rooms)]}
            )

        current = {}
        for monster in snapshot.monsters:
            current[monster.unit_id] = monster
            area = monster.area if monster.area is not None else here
            previous = self.present.get(monster.unit_id) or self.gone.pop(monster.unit_id, None)
            if previous is None:
                self.seen.setdefault(area, set()).add(monster.unit_id)
                event: dict[str, Any] = {
                    'event': 'seen',
                    't': t,
                    'unit_id': monster.unit_id,
                    'txt_id': monster.txt_id,
                    'mode': monster.mode,
                    'x': monster.x,
                    'y': monster.y,
                    'area': area,
                    'distance': distance(monster, location),
                }
                if monster.data_hex is not None:
                    event['data_hex'] = monster.data_hex
                if monster.stats is not None:
                    event['stats'] = [list(stat) for stat in monster.stats]
                if monster.base_stats is not None:
                    event['base_stats'] = [list(stat) for stat in monster.base_stats]
                if monster.room is not None:
                    event['room'] = list(monster.room)
                events.append(event)
                continue
            if monster.unit_id not in self.present:
                events.append(
                    {'event': 'back', 't': t, 'unit_id': monster.unit_id, 'mode': monster.mode}
                    | {'x': monster.x, 'y': monster.y, 'distance': distance(monster, location)}
                )
            if previous.mode not in DEAD_MODES and monster.mode in DEAD_MODES:
                self.killed[area] = self.killed.get(area, 0) + 1
                events.append(
                    {'event': 'died', 't': t, 'unit_id': monster.unit_id, 'txt_id': monster.txt_id, 'area': area}
                    | {'x': monster.x, 'y': monster.y, 'distance': distance(monster, location)}
                )
        for unit_id, monster in self.present.items():
            if unit_id in current:
                continue
            if not snapshot.complete:
                current[unit_id] = monster  # possibly missed by a broken-off walk: decide next pass
                continue
            self.gone[unit_id] = monster
            events.append(
                {'event': 'gone', 't': t, 'unit_id': unit_id, 'txt_id': monster.txt_id}
                | {'alive': monster.mode not in DEAD_MODES, 'x': monster.x, 'y': monster.y}
                | {'distance': distance(monster, location)}
            )
        self.present = current

        if self.next_summary is None:
            self.next_summary = now + self.summary_seconds
        elif now >= self.next_summary:
            self.next_summary = now + self.summary_seconds
            events.append(
                {
                    'event': 'summary',
                    't': t,
                    'area': here,
                    'present': len(current),
                    'alive': sum(m.mode not in DEAD_MODES for m in current.values()),
                    'seen': len(self.seen.get(here, ())),
                    'killed': self.killed.get(here, 0),
                    'rooms_loaded': len(snapshot.room2s),
                    'rooms_loaded_ever': len(rooms),
                    'level_rooms': self.level_rooms.get(here),
                }
            )
        return events

    def mark(self, now: float) -> dict[str, Any]:
        present = [[m.unit_id, m.txt_id, m.mode, m.x, m.y] for m in self.present.values()]
        return {'event': 'mark', 't': round(now, 3), 'area': self.area, 'present': present}


class TerrorProbe:
    def __init__(
        self,
        source,
        output,
        *,
        capture_lock: threading.Lock,
        poll_interval,
        summary_seconds=10.0,
        around_seconds=1.0,
        observe=observe_monsters,
        tracker=None,
        display=None,
        focused=None,
        show_unconfirmed=True,
        bosses=None,
        danger=True,
        elites=True,
        shards=None,
    ):
        self.source, self.output, self.capture_lock = source, output, capture_lock
        self.poll_interval, self.observe = poll_interval, observe
        self.ledger = MonsterLedger(summary_seconds=summary_seconds, around_seconds=around_seconds)
        self.level = None  # level pointer whose Room2s were counted
        self.last_poll = -math.inf
        self.last_warning = None
        self.tracker, self.display, self.focused = tracker, display, focused
        self.show_unconfirmed = show_unconfirmed
        self.bosses = bosses  # boss kills of this game launch (terror/bosses.py), shown under the Terror lines
        self.danger = danger  # warning rows for deadly packs above the Terror lines (terror/danger.py)
        self.elites = elites  # the level's elite groups under the Terror lines (terror/elites.py)
        self.shards = shards  # elite kills and Worldstone Shard drops, logged with the events (terror/shards.py)
        self.card: list[str] = []

    def poll(self, now):
        if now - self.last_poll < self.poll_interval or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        try:
            self.source.ensure_connected()
            snapshot = self.observe(
                self.source.pid,
                self.source.images,
                self.source.capture,
                known=self.ledger.known,
                counted_level=self.level,
                **({'item_classes': frozenset(self.shards.model.items)} if self.shards is not None else {}),
            )
        except Exception as exc:
            text = f'Terror probe: read failed: {exc}'
            if text != self.last_warning:
                LOG.warning('%s', text)
                self.last_warning = text
            return
        finally:
            self.capture_lock.release()
        location = snapshot.location
        # A level counts as read once its struct was: a read that failed on entry is tried again.
        if location is None:
            self.level = None
        elif snapshot.level_rooms is not None:
            self.level = location.level
        events = self.ledger.update(snapshot, now)
        if self.shards is not None:
            events += self.shards.update(events, now, items=snapshot.items, area=location and location.area_id)
        for event in events:
            if event['event'] == 'left_game' and event['killed']:
                LOG.info('Terror probe: game left; kills by area %s, seen %s', event['killed'], event['seen'])
        self.write(events)
        if self.tracker is not None:
            self.tracker.apply(events)
            if location is not None and snapshot.level_rooms is not None:
                self.tracker.level_read(location.area_id, snapshot.level_rooms, snapshot.level_hex or '')
            self.tracker.track(snapshot.monsters, snapshot.location, snapshot.complete, states=snapshot.player_states)
        if self.bosses is not None:
            self.bosses.apply(self.source.images.get('identity') or {'pid': self.source.pid}, events)
        self.card = self.card_lines(self.tracker, snapshot.location, snapshot.player_level)

    def card_lines(self, tracker, location, player_level=None) -> list[str]:
        if location is None:
            return []
        bosses = self.bosses.lines() if self.bosses is not None else []
        warnings = []
        if tracker is not None and self.danger:
            warnings = tracker.danger_lines(location.area_id, (location.x, location.y))
        terror = self.terror_lines(tracker, location, player_level) if tracker is not None else []
        elites = tracker.elite_line(location.area_id) if tracker is not None and self.elites else None
        return [*warnings, *terror, *([elites] if elites else []), *bosses]

    def terror_lines(self, tracker, location, player_level=None) -> list[str]:
        terrorized = tracker.terrorized(location.area_id)
        if terrorized is None and not self.show_unconfirmed:
            return []
        position = (location.x, location.y)
        return tracker.lines(location.area_id, terrorized=terrorized, position=position, player_level=player_level)

    def tick(self):
        if self.display is not None and (self.tracker is not None or self.bosses is not None):
            focused = self.focused is None or self.focused(self.source.images)
            self.display(self.card if focused else [])

    def mark(self, now):
        self.write([self.ledger.mark(now)])

    def write(self, events):
        if not events:
            return
        at = timestamp()
        with self.output.open('a', encoding='utf-8') as stream:
            for event in events:
                stream.write(json.dumps({'at': at, **event}, separators=(',', ':')) + '\n')
