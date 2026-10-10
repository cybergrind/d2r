"""Show where a level's point of interest is for a few seconds after entering the level.

What to point at lives in levels/handlers/ (one file per level). This module only decides
when: once per entry into a guided area, polled without waiting for the capture lock,
cleared after `seconds` or when D2R loses focus. Failures are logged at WARNING once
per distinct message; an earlier DEBUG-only version failed invisibly (2026-09-30).

The card is the arrow line(s) plus a level map (levels/level_map.py). While it is shown,
each poll re-reads only the player position and rebuilds both, so the dot and arrow follow.

Win+C calls `press()`: a single press on a shown card switches a big level between the view
around the player and the whole level (osd/level_map.py; user, 2026-10-06); with no card up it
shows the card again. Either way from a fresh room and position read,
in any level (levels without a handler get the map and their ways out, levels/exits.py), waiting
up to `lock_timeout` for the capture lock. Two presses within DOUBLE_PRESS seconds (hotkey
timestamps) toggle a pinned card: it never
expires, follows the player into every level (map only where no handler exists), hides while
D2R is unfocused, and is removed by the next double press. `pinned=True` starts that way
(`APPRAISAL.level_guide_pinned`, what `make serve` does).

Room details arrive late (the level behind an exit only once the player has been near it), so
while a card is shown the rooms are read again every ROOMS_REFRESH seconds and merged with what
this game already knew (levels/session.py): an exit named once stays named for the game. The
memory is dropped when the player is in no level (the menu between games).

Each entry into a guided area also yields one evidence record (levels/evidence.py), saved
after the capture lock is released; a failed lookup is recorded once even while retrying.
"""

import math
import threading
import time
from collections import OrderedDict

from inventory_tracking.common import LOG
from inventory_tracking.levels.evidence import evidence_record
from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.geometry import Pointer, pointer
from inventory_tracking.levels.level_map import build_map, centre
from inventory_tracking.levels.memory import observe_level
from inventory_tracking.levels.model import Guidance, Level, LevelSnapshot, Location, Target
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.session import LevelMemory, layout_key
from inventory_tracking.levels.spots import WAYS_OUT, on_waypoint, pinpoint
from inventory_tracking.osd.level_map import KIND_TONES
from inventory_tracking.presentation import StyledLine, Tone


def pointer_lines(pointers: list[Pointer]) -> list[StyledLine]:
    lines = []
    for p in pointers:
        tone = KIND_TONES.get(p.kind, Tone.POI)
        if p.here:
            lines.append(StyledLine(f'•  {p.label}: here', tone))
        else:
            lines.append(StyledLine(f'{p.arrow}  {p.label}: {p.compass}', tone, arrow=p.arrow))
    return lines


MAX_REMEMBERED_LEVELS = 32
DOUBLE_PRESS = 0.2  # seconds between two Win+C presses that toggle the pinned card (user, 2026-10-06)
ROOMS_REFRESH = 3.0  # seconds between room re-reads while a card is shown (exits get their names)


class LevelGuide:
    def __init__(
        self,
        source,
        *,
        capture_lock: threading.Lock,
        focused,
        display,
        seconds,
        poll_interval,
        clock=time.monotonic,
        observe=observe_level,
        evidence=None,
        observe_walls=None,
        library=None,
        visited_rooms=None,
        map_dots=None,
        on_rooms=None,
        observe_waypoints=None,
        pinned=False,
    ):
        self.source, self.capture_lock, self.focused, self.display = source, capture_lock, focused, display
        self.seconds, self.poll_interval, self.clock, self.observe = seconds, poll_interval, clock, observe
        self.area = None
        self.last_poll = -math.inf
        self.visible = None
        self.expires = 0.0
        self.last_warning = None
        self.evidence = evidence
        self.recorded = None  # (area, POI presets, problems) of the last saved record this entry
        self.shown = None  # (snapshot, pois) behind the visible card, for live position updates
        self.lock_timeout = 1.0  # seconds show() may wait for the capture lock
        self.pinned = pinned
        self.last_press = None  # hotkey timestamp of an unpaired press
        self.whole = False  # big levels: the whole level instead of the part around the player
        self.switched = False  # the unpaired press switched `whole`: a double press takes it back
        # Walkable tiles of loaded rooms, remembered for the current level (called under the capture lock).
        # The library (levels/walls.py) draws rooms of already-seen layouts before they load.
        self.observe_walls, self.library = observe_walls, library
        self.visited_rooms = visited_rooms  # area -> bounds of rooms the player was in or next to
        self.map_dots = map_dots  # area -> live MapPoi dots: monsters, Heralds (terror/tracker.py)
        # Called with (area, rooms) whenever a level's rooms are read: the rooms' pieces name the
        # level's fixed elite groups (terror/tracker.py level_layout).
        self.on_rooms = on_rooms
        # Waypoint objects seen in the current level, in tiles (called under the capture lock): the
        # waypoint POI moves from its room's centre onto the object once it is near (levels/spots.py).
        self.observe_waypoints, self.waypoints = observe_waypoints, set()
        self.walls = {}
        self.rooms = ()  # the current level's rooms, for the library
        # Walls read this game, per level: a trip to town must not lose generated terrain, which
        # the library never learns. Keyed by the level's layout (session.layout_key: room details
        # that load later don't change it), so a new game (other rooms) starts blank; the oldest
        # levels are dropped past MAX_REMEMBERED_LEVELS.
        self.level_walls: OrderedDict[tuple, dict] = OrderedDict()
        self.memory = LevelMemory()  # room details read this game (exits' levels, preset variants)
        self.rooms_read = -math.inf  # clock time of the last room read

    def _enter_rooms(self, area, rooms):
        """A fresh room list for the current level: seed walls from the library, then read live."""
        self.rooms = tuple(rooms)
        if self.on_rooms is not None and area is not None and self.rooms:
            self.on_rooms(area, self.rooms)
        key = layout_key(area, self.rooms)
        self.walls = self.level_walls.setdefault(key, {})
        self.level_walls.move_to_end(key)
        while len(self.level_walls) > MAX_REMEMBERED_LEVELS:
            self.level_walls.popitem(last=False)
        if self.library is not None:
            for grid in self.library.known(self.rooms):
                self.walls.setdefault((grid.x, grid.y), grid)
        self.waypoints = set()
        self._read_walls()
        self._read_waypoints()

    def _read_rooms(self):
        """(location, the level's rooms merged with what this game already knew about them)."""
        location, rooms = self.observe(self.source.pid, self.source.images, self.source.capture, rooms=True)
        self.rooms_read = self.clock()
        return location, self.memory.merge(location.area_id, rooms) if location else ()

    def _refresh_rooms(self):
        """While a card is shown: re-read the rooms now and then, and re-mark when they say more."""
        if self.clock() - self.rooms_read < ROOMS_REFRESH:
            return
        snapshot, _ = self.shown
        location, rooms = self._read_rooms()
        if location is None or location.area_id != self.area or not rooms or rooms == snapshot.rooms:
            return
        self.rooms = rooms
        if self.on_rooms is not None:
            self.on_rooms(self.area, rooms)  # the pieces' files are read as rooms load
        handler = handler_for(self.area)
        snapshot = LevelSnapshot(location, rooms)
        guidance = guide_level(handler, snapshot)
        for problem in guidance.problems:
            self.warn('%s (%s): %s', handler.name, self.area, problem)
        self.shown = (snapshot, tuple(pinpoint(poi) for poi in guidance.pois))

    def _read_walls(self):
        if self.observe_walls is None:
            return
        try:
            grids = list(self.observe_walls(self.source.pid, self.source.images, self.source.capture))
            for grid in grids:
                self.walls[grid.x, grid.y] = grid
            if self.library is not None:
                self.library.learn(self.rooms, grids)
        except Exception as exc:
            self.warn('walls not read: %s', exc)

    def _read_waypoints(self):
        if self.observe_waypoints is None:
            return
        try:
            self.waypoints.update(self.observe_waypoints(self.source.pid, self.source.images, self.source.capture))
        except Exception as exc:
            self.warn('waypoints not read: %s', exc)

    def warn(self, message, *args):
        text = message % args
        if text != self.last_warning:
            LOG.warning('Level guide: %s', text)
            self.last_warning = text

    def poll(self, now):
        if now - self.last_poll < self.poll_interval or not self.capture_lock.acquire(blocking=False):
            return
        self.last_poll = now
        record = None
        try:
            self.source.ensure_connected()
            if self.focused(self.source.images):
                record = self._observe()
        except Exception as exc:
            self.warn('read failed: %s', exc)
        finally:
            self.capture_lock.release()
        if record is not None and self.evidence is not None:
            try:
                self.evidence(record)
            except Exception as exc:
                self.warn('evidence not saved: %s', exc)

    def _observe(self):
        location, _ = self.observe(self.source.pid, self.source.images, self.source.capture)
        area = location.area_id if location else None
        if area == self.area:
            if self.visible is not None and self.shown is not None and location is not None:
                self._read_walls()
                self._read_waypoints()
                self._refresh_rooms()
                self.visible = self._card(location)
            return None
        if location is None:
            self.memory.reset()  # the menu: the next game's levels are new
        self.walls, self.rooms = {}, ()  # a new level (or leaving one): forget its rooms
        handler = handler_for(area)
        if handler is None:
            self.area, self.recorded = area, None
            if self.pinned and location is not None:
                self._show_map(location)
            return None
        location, rooms = self._read_rooms()
        if location is None or location.area_id != area:
            return None  # left again between reads; the next poll sees the new area
        snapshot = LevelSnapshot(location, rooms)
        self._enter_rooms(area, snapshot.rooms)
        guidance = guide_level(handler, snapshot)
        for problem in guidance.problems:
            self.warn('%s (%s): %s', handler.name, area, problem)
        key = (area, tuple(p.room.preset for p in guidance.pois), guidance.problems)
        record = None if key == self.recorded else evidence_record(snapshot, handler, guidance)
        self.recorded = key
        if not guidance.pois and not self.pinned:
            if rooms and not guidance.problems:
                self.area = area  # nothing to mark here (Lower Kurast without a camp): don't re-read
            return record  # otherwise the area stays unmarked, so the next poll retries (rooms may still be loading)
        self.area = area
        self._present(snapshot, guidance)
        status = '' if handler.confirmed else ' (unconfirmed)'
        LOG.info('Level guide: %s%s — %s', handler.name, status, '; '.join(line.text for line in self.visible[:-1]))
        return record

    def _show_map(self, location: Location):
        """Pinned card entering an unguided level: read its rooms and show the map with its ways out."""
        location, rooms = self._read_rooms()
        if location is not None and rooms:
            self._enter_rooms(location.area_id, rooms)
            snapshot = LevelSnapshot(location, rooms)
            self._present(snapshot, guide_level(None, snapshot))

    def _present(self, snapshot: LevelSnapshot, guidance: Guidance):
        self.shown = (snapshot, tuple(pinpoint(poi) for poi in guidance.pois))
        self.visible, self.expires = self._card(snapshot.location), self.clock() + self.seconds

    def press(self, requested_at: float) -> bool:
        """Win+C. A double press toggles the pinned card; a single one switches a shown card between
        the view around the player and the whole level, or shows the card. True if a card is up."""
        double = self.last_press is not None and 0 <= requested_at - self.last_press <= DOUBLE_PRESS
        self.last_press = None if double else requested_at
        if not double:
            self.switched = self.visible is not None
            if self.switched:
                self.whole = not self.whole
            return self.show()
        if self.switched:  # the first press of the pair was not a view switch after all
            self.whole, self.switched = not self.whole, False
            if self.visible is not None and self.shown is not None:
                self.visible = self._card(self.shown[0].location)
        self.pinned = not self.pinned
        LOG.info('Level guide: map %s', 'pinned' if self.pinned else 'unpinned')
        if not self.pinned:
            self.visible = None
            self.display([])
            return True
        return self.visible is not None or self.show()

    def show(self) -> bool:
        """Show the card now (Win+C): fresh rooms and position, any level. False if nothing shown."""
        if not self.capture_lock.acquire(timeout=self.lock_timeout):
            self.warn('map not shown: capture busy')
            return False
        try:
            self.source.ensure_connected()
            location, rooms = self._read_rooms()
            self._enter_rooms(location.area_id if location else None, rooms)
        except Exception as exc:
            self.warn('map not shown: %s', exc)
            return False
        finally:
            self.capture_lock.release()
        if location is None or not rooms:
            return False
        snapshot = LevelSnapshot(location, rooms)
        handler = handler_for(location.area_id)
        guidance = guide_level(handler, snapshot)
        for problem in guidance.problems:
            self.warn('%s (%s): %s', handler.name, location.area_id, problem)
        # Mark the area as entered so the next poll only moves the dot instead of re-announcing.
        self.area = location.area_id
        self._present(snapshot, guidance)
        return True

    def _card(self, location: Location) -> list:
        snapshot, pois = self.shown
        pois = tuple(on_waypoint(poi, self.waypoints) for poi in pois)
        visited = self.visited_rooms(location.area_id) if self.visited_rooms is not None else None
        dots = self.map_dots(location.area_id) if self.map_dots is not None else ()
        card = build_map(
            snapshot,
            pois,
            location,
            self.walls.values(),
            visited=visited,
            dots=dots,
            pid=self.source.pid,
            whole=self.whole,
        )
        return [*pointer_lines([pointer(poi, location) for poi in pois]), card]

    def target(self) -> Target | None:
        """The shown card's first mark, the one the first arrow line points at (the teleport step, macros/teleport.py).
        None with no card up or nothing marked. Read from the macro's thread: one reference, no lock."""
        shown = self.shown
        if shown is None or not shown[1]:
            return None
        snapshot, pois = shown
        poi = on_waypoint(pois[0], self.waypoints)
        warp = poi.kind in WAYS_OUT and poi.spot is not None
        point = poi.spot or centre(poi.room)
        return Target(snapshot.location.area_id, snapshot.rooms, point, poi.label, poi.kind, warp, self._ground())

    def level(self) -> Level | None:
        """The shown card's level: its rooms and the walls read so far, for a macro that chooses its own
        mark (the seek step and attack mode, macros/hunt.py). None with no card up. Read from the macro's thread."""
        shown = self.shown
        if shown is None:
            return None
        snapshot, _ = shown
        return Level(snapshot.location.area_id, snapshot.rooms, self._ground())

    def _ground(self) -> tuple:
        """The walkable grids read so far, copied while the service thread may add to them."""
        for _ in range(3):
            try:
                return tuple(self.walls.values())
            except RuntimeError:  # changed size during iteration
                continue
        return ()

    def dismiss(self):
        self.visible, self.pinned = None, False

    def tick(self):
        if self.visible is None:
            return
        if not self.pinned and self.clock() >= self.expires:
            self.visible = None
            self.display([])
        elif not self.focused(self.source.images):
            if not self.pinned:
                self.visible = None
            self.display([])  # a pinned card comes back when D2R has focus again
        else:
            self.display(self.visible)
