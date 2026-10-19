"""Show where a level's point of interest is for a few seconds after entering the level.

What to point at lives in levels/handlers/ (one file per level). This module only decides
when: once per entry into a guided area, polled without waiting for the capture lock,
cleared after `seconds` or when D2R loses focus. Failures are logged at WARNING once
per distinct message; an earlier DEBUG-only version failed invisibly (2026-09-30).

The card is the arrow line(s) plus a level map (levels/level_map.py). While it is shown,
each poll re-reads only the player position and rebuilds both, so the dot and arrow follow.
With `goals` (macros/card_goal.py) the first row is the route's goal, the one the macro goes to: a boss
where the tracker has him, nothing known of him a row without an arrow, no goal left (loot, leave, the
script over) no goal row and no route line; the marks of stages done have no row. A goal that changes
rebuilds the card at the next poll, the walls as they are (rca/2026-10-14/run-1916-hud-findings.md §1).

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

The walls and the card itself are read and rebuilt at most every `refresh_interval` seconds while
the character stays in the level (the waypoints every poll), or sooner once it has moved REFRESH_MOVE world units
(a room's width: the rooms loaded around it then change) or the rooms said more. 0 (the default)
is every poll; the service sets 2 s while the macro works (appraisal/cadence.py; the 0.5 s re-read
was the biggest of the service's slow passes during a level run, rca/2026-10-13/latency-findings.md).
The area itself is still read every poll: a new level is seen as soon as before.

Each entry into a guided area also yields one evidence record (levels/evidence.py), saved
after the capture lock is released; a failed lookup is recorded once even while retrying.
"""

import itertools
import math
import threading
import time
from collections import OrderedDict
from dataclasses import replace

from inventory_tracking.common import LOG
from inventory_tracking.levels.evidence import evidence_record
from inventory_tracking.levels.exits import guide_level, passage_of
from inventory_tracking.levels.geometry import Pointer, pointer
from inventory_tracking.levels.level_map import build_map, centre
from inventory_tracking.levels.memory import observe_level
from inventory_tracking.levels.model import Guidance, Lead, Level, LevelSnapshot, Location, Poi, Room, Target
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.session import LevelMemory, layout_key
from inventory_tracking.levels.spots import WAYS_OUT, on_waypoint, pinpoint
from inventory_tracking.native.layout import TILE_UNITS
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


def place(poi: Poi) -> tuple[float, float]:
    """Where the mark is, in tiles: what the teleport step is given as `Target.point`."""
    return poi.spot or centre(poi.room)


# Marks of one label the shortest way through is worked out for, every order tried (7! = 5040 at most, a few ms: the
# card asks at every refresh); past it the nearest leads. Lower Kurast has two camps of three chests.
TOUR_MARKS = 7


def tour_first(marks: list[Poi], here: tuple[float, float]) -> Poi:
    """The mark the shortest way from `here` (tiles) through all of `marks` begins with; the nearest past
    TOUR_MARKS. The loop's game of 2026-10-16 19:56 went nearest first through Lower Kurast's six camp chests, 353
    units against 266 the shortest way (rca/2026-10-16/loop-chests-findings.md §3); asked again at every mark, the
    way stays the shortest."""
    if len(marks) > TOUR_MARKS:
        return min(marks, key=lambda poi: math.dist(here, place(poi)))

    def length(order: tuple[Poi, ...]) -> float:
        points = (here, *(place(poi) for poi in order))
        return sum(math.dist(a, b) for a, b in itertools.pairwise(points))

    return min(itertools.permutations(marks), key=length)[0]


def lead_first(pois: tuple[Poi, ...], lead: Lead | None, here: tuple[float, float] | None = None) -> tuple[Poi, ...]:
    """`pois` with the mark `lead` names put first (levels/routes.md: the stage a route is at); as
    they are when it names none of them. Of several with the label, the one leading to the level
    meant, and of those the first of the shortest way from `here` (tiles) through them all (`tour_first`:
    Lower Kurast's two camps, a hell pit's chests), the card's order without it. A way back that is led
    with is a way on: the route goes through it (Outer Cloister to the Monastery Gate), and the teleport step refuses a
    first mark that only leads back. Marks at the places the lead says are done with (`Lead.skip`:
    chests opened) are passed for the next."""
    named = [poi for poi in pois if poi.label == lead.label and place(poi) not in lead.skip] if lead else []
    if lead is None or not named:
        return pois
    meant = [poi for poi in named if poi.area == lead.area] or named
    first = meant[0] if here is None else tour_first(meant, here)
    rest = tuple(poi for poi in pois if poi is not first)
    return (replace(first, kind='stairs') if first.kind == 'previous' else first, *rest)


def goal_rows(goal, first: Poi | None, kept: tuple[Poi, ...], location: Location):
    """(the card's rows, the route line's end in tiles or None) with the route's goal
    first (macros/goals.py `route_goal`, duck-typed: `label`, `place` in world units, `unit`, `known`, `mark`,
    `stage`). On the card's first mark itself: that mark's row. At a unit (a boss where the tracker has him) or
    another place: a row of its own toward it, the mark it was made from dropped. Nothing known of where it is:
    a row with no arrow. None (loot, leave, the script over): no goal row, no route line; the other marks keep
    their rows (ways back, extras: information, not goals)."""
    if goal is None:
        return pointer_lines([pointer(poi, location) for poi in kept]), None
    mark = goal.mark.label if goal.mark is not None else None
    rest = [pointer(poi, location) for poi in kept if not (first is not None and poi is first and mark == first.label)]
    if not goal.known:
        name = goal.stage.boss if goal.stage is not None and goal.stage.boss else goal.label
        return [StyledLine(f'{name}: not seen', KIND_TONES['target']), *pointer_lines(rest)], None
    toward = (goal.place[0] / TILE_UNITS, goal.place[1] / TILE_UNITS)
    if first is not None and mark == first.label and goal.unit is None and math.dist(toward, place(first)) < 1:
        return pointer_lines([pointer(first, location), *rest]), toward
    dx, dy = goal.place[0] - location.x, goal.place[1] - location.y
    return pointer_lines([Pointer(goal.label, None, dx, dy, False, 'target'), *rest]), toward


MAX_REMEMBERED_LEVELS = 32
DOUBLE_PRESS = 0.2  # seconds between two Win+C presses that toggle the pinned card (user, 2026-10-06)
ROOMS_REFRESH = 3.0  # seconds between room re-reads while a card is shown (exits get their names)
REFRESH_MOVE = 40  # world units (sub-tiles) moved that make the walls due before `refresh_interval`: a room's width


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
        lead=None,
        goals=None,
        observe_things=None,
    ):
        self.source, self.capture_lock, self.focused, self.display = source, capture_lock, focused, display
        self.seconds, self.poll_interval, self.clock, self.observe = seconds, poll_interval, clock, observe
        self.area: int | None = None
        self.last_poll = -math.inf
        self.visible: list | None = None
        self.expires = 0.0
        self.last_warning = None
        self.evidence = evidence
        self.recorded = None  # (area, POI presets, problems) of the last saved record this entry
        # (snapshot, pois) behind the visible card, for live position updates
        self.shown: tuple[LevelSnapshot, tuple[Poi, ...]] | None = None
        # Where the last poll found the character on the shown card's level: the route's mark of several with its
        # label is the nearest to it (`_marks`); the card's snapshot keeps where it stood when its rooms were read.
        self.here: Location | None = None
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
        self.rooms: tuple[Room, ...] = ()  # the current level's rooms, for the library
        # Walls read this game, per level: a trip to town must not lose generated terrain, which
        # the library never learns. Keyed by the level's layout (session.layout_key: room details
        # that load later don't change it), so a new game (other rooms) starts blank; the oldest
        # levels are dropped past MAX_REMEMBERED_LEVELS.
        self.level_walls: OrderedDict[tuple, dict] = OrderedDict()
        # area -> the mark to lead the card with, or None: the stage a route is at there (routes/progress.py).
        # Asked at every card and every target, so the arrow and the teleport step never disagree.
        self.lead = lead
        # The route's goal and the marks done with (macros/card_goal.py CardGoals: `goal`, `done`, `wanted`, `note`):
        # the card's first row points at the goal the macro goes to, the done marks have no row, and no goal left
        # is no arrow (rca/2026-10-14/run-1916-hud-findings.md §1). None: the rows are the marks in `_marks` order.
        self.goals = goals
        # (pid, images, capture, classes) -> the object units of those classes near the player (macros/world.py
        # `observe_things`), read at each poll for the marks `goals.wanted` names: a seal opened by hand is done.
        self.observe_things = observe_things
        self.drawn: tuple | None = None  # the goal and done marks the visible card was drawn with
        self.memory = LevelMemory()  # room details read this game (exits' levels, preset variants)
        self.rooms_read = -math.inf  # clock time of the last room read
        # Seconds between re-reads of the walls and rebuilds of the card while it is shown in the same level;
        # 0 every poll (set by the service's cadence, appraisal/cadence.py).
        self.refresh_interval = 0.0
        self.refreshed: tuple[float, tuple[int, int] | None] = (-math.inf, None)  # (clock, where) of the last

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
        self.refreshed = (self.clock(), None)

    def _refresh_due(self, location: Location) -> bool:
        """Whether the walls and the card are read again at this poll (`refresh_interval`, REFRESH_MOVE)."""
        at, where = self.refreshed
        if self.clock() - at >= self.refresh_interval:
            return True
        return where is not None and math.hypot(location.x - where[0], location.y - where[1]) >= REFRESH_MOVE

    def _read_rooms(self) -> tuple[Location | None, tuple[Room, ...]]:
        """(location, the level's rooms merged with what this game already knew about them)."""
        location, rooms = self.observe(self.source.pid, self.source.images, self.source.capture, rooms=True)
        self.rooms_read = self.clock()
        return location, self.memory.merge(location.area_id, rooms) if location else ()

    def _refresh_rooms(self) -> bool:
        """While a card is shown: re-read the rooms now and then, and re-mark when they say more (True)."""
        if self.clock() - self.rooms_read < ROOMS_REFRESH:
            return False
        assert self.shown is not None  # called only while a card is shown
        snapshot, _ = self.shown
        location, rooms = self._read_rooms()
        if location is None or location.area_id != self.area or not rooms or rooms == snapshot.rooms:
            return False
        self.rooms = rooms
        if self.on_rooms is not None:
            self.on_rooms(self.area, rooms)  # the pieces' files are read as rooms load
        snapshot = LevelSnapshot(location, rooms)
        guidance = self._guide(location.area_id, snapshot)
        self.shown = (snapshot, tuple(pinpoint(poi) for poi in guidance.pois))
        self._absent(location.area_id, guidance)
        return True

    def _guide(self, area: int, snapshot: LevelSnapshot) -> Guidance:
        """`guide_level` with the area's handler, its problems warned (a level without one has none)."""
        handler = handler_for(area)
        guidance = guide_level(handler, snapshot)
        if handler is not None:
            for problem in guidance.problems:
                self.warn('%s (%s): %s', handler.name, area, problem)
        return guidance

    def _read_walls(self):
        if self.observe_walls is None:
            return
        try:
            grids = list(self.observe_walls(self.source.pid, self.source.images, self.source.capture))
            # Only the grids not already held as they are (the reader gives an unchanged room back as the
            # same object, levels/memory.py `walkable_tiles`) are stored and taught to the library.
            fresh = [grid for grid in grids if self.walls.get((grid.x, grid.y)) is not grid]
            for grid in fresh:
                self.walls[grid.x, grid.y] = grid
            if self.library is not None and fresh:
                self.library.learn(self.rooms, fresh)
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
            if location is not None:
                self.here = location
            if self.visible is not None and self.shown is not None and location is not None:
                renamed = self._refresh_rooms()
                # Every poll: the teleport step's mark moves onto a waypoint's object as soon as it is seen (`target`).
                self._read_waypoints()
                self._read_progress(location)
                if renamed or self._refresh_due(location):
                    self._read_walls()
                    self.refreshed = (self.clock(), (location.x, location.y))
                    self.visible = self._card(location)
                elif self.goals is not None and self._goal(location)[3] != self.drawn:
                    self.visible = self._card(location)  # the goal changed: at once, the walls as they are
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
        card = self._present(snapshot, guidance)
        status = '' if handler.confirmed else ' (unconfirmed)'
        LOG.info('Level guide: %s%s — %s', handler.name, status, '; '.join(line.text for line in card[:-1]))
        return record

    def _show_map(self, location: Location):
        """Pinned card entering an unguided level: read its rooms and show the map with its ways out."""
        now, rooms = self._read_rooms()
        if now is not None and rooms:
            self._enter_rooms(now.area_id, rooms)
            snapshot = LevelSnapshot(now, rooms)
            self._present(snapshot, guide_level(None, snapshot))

    def _present(self, snapshot: LevelSnapshot, guidance: Guidance) -> list:
        """Show `guidance` for `snapshot`; the card shown."""
        self.shown = (snapshot, tuple(pinpoint(poi) for poi in guidance.pois))
        self._absent(snapshot.location.area_id, guidance)
        self.refreshed = (self.refreshed[0], (snapshot.location.x, snapshot.location.y))  # the walls were read here
        card = self._card(snapshot.location)
        self.visible, self.expires = card, self.clock() + self.seconds
        return card

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
        guidance = self._guide(location.area_id, snapshot)
        # Mark the area as entered so the next poll only moves the dot instead of re-announcing.
        self.area = location.area_id
        self._present(snapshot, guidance)
        return True

    def _marks(self, snapshot: LevelSnapshot, pois: tuple[Poi, ...]) -> tuple[Poi, ...]:
        """The card's marks in the order shown: waypoints on their objects, the route's mark first, the nearest
        of its label to where the shown card has the character."""
        pois = tuple(on_waypoint(poi, self.waypoints) for poi in pois)
        if self.lead is None:
            return pois
        location, polled = snapshot.location, self.here
        if polled is not None and polled.area_id == location.area_id:
            location = polled
        here = (location.x / TILE_UNITS, location.y / TILE_UNITS)
        return lead_first(pois, self.lead(location.area_id), here)

    def _absent(self, area: int, guidance: Guidance) -> None:
        """Tell the route's goals the marks the level is known to have none of (`Guidance.absent`), with the card it
        is shown with: the stage on them is done before the macro's next look at the card."""
        if self.goals is not None and guidance.absent:
            self.goals.absent(area, guidance.absent)

    def _read_progress(self, location: Location) -> None:
        """At each poll with a card up: tell the route's progress what is done whoever did it (macros/card_goal.py
        `note`): a mark stood at, and the objects of its `use` marks read (`observe_things`) when any is left."""
        if self.goals is None or self.shown is None:
            return
        snapshot, pois = self.shown
        area = snapshot.location.area_id
        if area != location.area_id:
            return
        marks = tuple(on_waypoint(poi, self.waypoints) for poi in pois)
        things = ()
        classes = self.goals.wanted(area, (location.x, location.y), marks)
        if classes and self.observe_things is not None:
            try:
                things = self.observe_things(self.source.pid, self.source.images, self.source.capture, classes)
            except Exception as exc:
                self.warn('objects not read: %s', exc)
        self.goals.note(area, (location.x, location.y), marks, things)

    def _goal(self, location: Location):
        """(the marks in card order, the route's goal or None, the marks done with, the key the card is drawn
        with): `goals` asked from where the character is, with the teleport step's mark (`target`) as the card's."""
        assert self.shown is not None
        snapshot, pois = self.shown
        area = snapshot.location.area_id
        pois = self._marks(snapshot, pois)
        if self.goals is None:
            return pois, None, (frozenset(), frozenset()), None
        first = self._target_of(snapshot, pois[0]) if pois else None
        goal = self.goals.goal(area, (location.x, location.y), first)
        done = self.goals.done(area)
        aim = None
        if goal is not None:
            mark = goal.mark.label if goal.mark is not None else None
            # A unit's goal moves with it: the card follows it at its own pace, not at each step it takes.
            where = None if goal.unit is not None else (round(goal.place[0]), round(goal.place[1]))
            aim = (goal.label, goal.unit, goal.known, mark, where)
        return pois, goal, done, (area, aim, done)

    def _card(self, location: Location) -> list:
        assert self.shown is not None
        snapshot, _ = self.shown
        pois, goal, (labels, places), self.drawn = self._goal(location)
        kept = tuple(poi for poi in pois if poi.label not in labels and (poi.label, place(poi)) not in places)
        rows, toward = pointer_lines([pointer(poi, location) for poi in kept]), None
        if self.goals is not None:
            rows, toward = goal_rows(goal, pois[0] if pois else None, kept, location)
        visited = self.visited_rooms(location.area_id) if self.visited_rooms is not None else None
        dots = self.map_dots(location.area_id) if self.map_dots is not None else ()
        card = build_map(
            snapshot,
            kept,
            location,
            self.walls.values(),
            visited=visited,
            dots=dots,
            pid=self.source.pid,
            whole=self.whole,
            toward=toward,
            routed=self.goals is None or toward is not None,
            units=self._units(location.area_id),
        )
        return [*rows, card]

    def _units(self, area: int) -> tuple[int, int] | None:
        """(unit table address, area) for the HUD's own walk of the monster table (hud/live.py), with dots shown."""
        if self.map_dots is None:
            return None
        tables = {found.get('table_address') for found in (self.source.capture or {}).get('unit_table_candidates', ())}
        return (tables.pop(), area) if len(tables) == 1 and None not in tables else None

    def _target_of(self, snapshot: LevelSnapshot, poi: Poi) -> Target:
        # An entrance kept as a side trip is a door too (Poi.entrance): as a mere place, Crystalline Passage's way into
        # Frozen River was stood beside and never gone through, "TZ next level" again and again, the game left (09:32:49
        # and every game after on 2026-10-19)
        warp = (poi.kind in WAYS_OUT or poi.entrance) and poi.spot is not None
        area, mark = snapshot.location.area_id, place(poi)
        passage = passage_of(area, snapshot.rooms, poi, mark)
        into = poi.area if passage is not None else None
        return Target(area, snapshot.rooms, mark, poi.label, poi.kind, warp, self._ground(), poi.use, passage, into)

    def target(self) -> Target | None:
        """The shown card's first mark, the one the first arrow line points at (the teleport step, macros/teleport.py).
        None with no card up or nothing marked. Read from the macro's thread: one reference, no lock."""
        shown = self.shown
        if shown is None or not shown[1]:
            return None
        snapshot, pois = shown
        return self._target_of(snapshot, self._marks(snapshot, pois)[0])

    def marks(self, label: str) -> tuple[tuple[float, float], ...]:
        """The places of the shown card's marks with `label` (a hell pit's chests), in tiles: the
        route step sees from them when each was used (macros/route.py). Read from the macro's thread."""
        shown = self.shown
        if shown is None:
            return ()
        return tuple(place(poi) for poi in shown[1] if poi.label == label)

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
