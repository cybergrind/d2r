"""Handler building blocks. A level handler file declares HANDLERS with these helpers.

A POI spec is a full-match regex over bundled LvlPrest names, never a single Def: boss and
stairs rooms exist once per doorway orientation (Arcane Summoner N/S/E/W = 525-528; game 1
used 527, game 2 used 525). A required POI that matches no room, or several, is a problem
for the framework to log; it is never guessed. Optional POIs (waypoints) are silent when absent.
Chunks of one large preset (8x8 Room2s sharing the preset's bounds, e.g. a 40x40 Temple
quadrant) count as one match, and the POI covers the whole preset. A preset that comes in
DS1 variants can place its POI by variant: `sides` maps the file index (lvlprest File1..
order) to the edge of the preset the POI is on (map axes, north = -y). `variants` restricts a
spec to some DS1 variants, and `each` marks every matching instance instead of requiring one.

A level with logic that doesn't fit a pattern can subclass Handler and override `guide`.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from inventory_tracking.levels.model import Guidance, LevelSnapshot, Poi, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.spots import pinpoint
from inventory_tracking.native.layout import TILE_UNITS


@dataclass(frozen=True)
class PoiSpec:
    label: str
    pattern: str
    kind: str = 'target'
    optional: bool = False
    family: str | None = None  # every matching preset name must start with it (checked offline)
    sides: tuple[str, ...] = ()  # per DS1 variant: 'N'/'S'/'E'/'W' edge of the preset holding the POI
    inset: float | None = None  # how far inside that edge (fraction of the preset); None = SIDE_INSET
    variants: tuple[int, ...] = ()  # only these DS1 variants (file index) match; empty = any
    each: bool = False  # mark every matching instance (none is fine), e.g. Lower Kurast's camps
    warp: bool = False  # an entrance of another kind (a side trip as 'target'): mark its warp tile too

    def matches(self, name: str) -> bool:
        return re.fullmatch(self.pattern, name) is not None


@dataclass(frozen=True)
class Handler:
    name: str
    areas: frozenset[int]
    pois: tuple[PoiSpec, ...]
    confirmed: bool = False  # True only when a real fixture test replays it

    def guide(self, snapshot: LevelSnapshot) -> Guidance:
        pois, problems = [], []
        for spec in self.pois:
            start = len(pois)
            groups = instances(room for room in snapshot.rooms if spec.matches(preset_name(room.preset)))
            if spec.variants:
                groups = [group for group in groups if group[0].variant in spec.variants]
            found = [room for room, _ in groups]
            if spec.each:
                pois.extend(Poi(spec.label, room, spec.kind) for room in found)
            elif len(found) == 1 and spec.sides:
                room = found[0]
                if room.variant is None or room.variant >= len(spec.sides):
                    problems.append(f'{spec.label}: layout variant unknown')
                else:
                    side = spec.sides[room.variant]
                    inset = SIDE_INSET if spec.inset is None else spec.inset
                    pois.append(Poi(spec.label, side_room(room, side, inset), spec.kind))
            elif len(found) == 1 and whole_level_around(groups[0], snapshot):
                # The target is a whole-level layout the player stands in (Tower Cellar 5's
                # Countess): no direction. Any smaller preset the player stands in (the waypoint
                # they arrived by, WSK's 16x16 stairs) is a normal POI, shown as "here".
                if spec.optional:
                    continue
                problems.append(
                    f'{spec.label}: the preset is the whole area around the player (variant {found[0].variant})'
                )
            elif len(found) == 1:
                pois.append(Poi(spec.label, found[0], spec.kind))
            elif found:
                noun = 'areas' if any(room.block for room in found) else 'rooms'
                problems.append(f'{spec.label}: {len(found)} {noun} match')
            elif not spec.optional:
                problems.append(f'{spec.label}: no room matches')
            if spec.warp:
                pois[start:] = [pinpoint(poi, warp=True) for poi in pois[start:]]
        return Guidance(tuple(pois), tuple(problems))


def instances(rooms: Iterable[Room]) -> list[tuple[Room, int]]:
    """(room, chunk count) per preset instance: chunks sharing a block collapse into one room covering it."""
    found: dict[tuple, list] = {}
    for room in rooms:
        if room.block is None:
            found[room.preset, room.x, room.y] = [room, 1]
        else:
            key = (room.preset, room.block)
            if key in found:
                found[key][1] += 1
            else:
                found[key] = [Room(room.preset, *room.block, room.variant, room.block, room.leads_to), 1]
    return [(room, count) for room, count in found.values()]


def whole_level_around(group: tuple[Room, int], snapshot: LevelSnapshot) -> bool:
    """A multi-chunk preset taking at least half the level's room area, with the player inside."""
    room, chunks = group
    total = sum(r.width * r.height for r in snapshot.rooms)
    return chunks > 1 and 2 * room.width * room.height >= total > 0 and contains(room, snapshot.location)


def contains(room: Room, location) -> bool:
    tx, ty = location.x / TILE_UNITS, location.y / TILE_UNITS
    return room.x <= tx < room.x + room.width and room.y <= ty < room.y + room.height


SIDE_INSET = 0.15  # the POI sits this fraction of the preset's size inside the named edge


def side_room(room: Room, side: str, inset: float = SIDE_INSET) -> Room:
    """An 8x8 marker room `inset` inside one edge of `room` (x grows east, y grows south)."""
    fx = {'E': 1 - inset, 'W': inset}.get(side, 0.5)
    fy = {'S': 1 - inset, 'N': inset}.get(side, 0.5)
    x, y = round(room.x + room.width * fx) - 4, round(room.y + room.height * fy) - 4
    # The block keeps the preset's origin, so a warp spot (levels/spots.py) still finds its tile.
    block = room.block or (room.x, room.y, room.width, room.height)
    return Room(room.preset, x, y, 8, 8, room.variant, block)


def target(
    name: str,
    *,
    areas: Iterable[int],
    label: str,
    preset: str,
    confirmed=False,
    extra: Iterable[PoiSpec] = (),
    sides: Iterable[str] = (),
    kind: str = 'target',
    inset: float | None = None,
) -> Handler:
    """One POI: the unique room (or preset instance) whose preset name fully matches `preset`.

    kind='stairs' when the target leads to the next level (an entrance or an exit quadrant).
    """
    spec = PoiSpec(label, preset, kind, sides=tuple(sides), inset=inset)
    return Handler(name, frozenset(areas), (spec, *extra), confirmed)


def stairs_down(
    name: str, *, areas: Iterable[int], family: str, confirmed=False, extra: Iterable[PoiSpec] = (), word='Next'
) -> Handler:
    """The maze stairs down: '<family> Next N/S/E/W' ('Down' in Act 1 caves such as the Pit)."""
    spec = PoiSpec('Next level', rf'{re.escape(family)} {word} [NSEW]', 'stairs', family=family)
    return Handler(name, frozenset(areas), (spec, *extra), confirmed)


def previous(family: str, label: str) -> PoiSpec:
    """The way back: '<family> Prev …' stairs up, labelled with where they lead (e.g. 'Barracks')."""
    return PoiSpec(label, rf'{re.escape(family)} Prev [NSEW]+', 'previous', family=family)


def waypoint(family: str) -> PoiSpec:
    """Optional extra POI: '<family> Waypoint …' (spelled 'waypoint' in some families)."""
    return PoiSpec('Waypoint', rf'{re.escape(family)} [Ww]aypoint.*', 'waypoint', optional=True, family=family)


# Act 1 wilderness border presets whose open DS1 files (Bord*o.ds1 = 3, Bord*oe.ds1 = 4) are the
# walkable gaps between levels (D2MOO DrlgOutPlace: level links pick file 3, or 4 in the Burial
# Grounds; Black Marsh and Cold Plains evidence: one variant-3 border room per exit).
ACT1_GAP = r'Act 1 - Wild Border [1-4]'
# Act 4 Mesa borders have one open DS1 file (Border*o.ds1 = 3) and no 'oe' file (d2data lvlprest).
ACT4_GAP = r'Act 4 - Mesa Border [1-4]'


@dataclass(frozen=True)
class Exit:
    area: int
    label: str
    kind: str = 'stairs'


@dataclass(frozen=True)
class ExitsHandler(Handler):
    """Outdoor level: every open border gap is a POI (before the `pois` specs).

    A gap is named by the level behind it (Room.leads_to, readable only once the player has been
    near that edge); the last unknown gap takes the last unseen exit by elimination; any other
    gap is a plain 'Exit'. Missing or extra gaps are not problems: the gaps are what the level has.
    """

    exits: tuple[Exit, ...] = ()
    gap: str = ACT1_GAP
    gap_variants: tuple[int, ...] = (3, 4)

    def guide(self, snapshot: LevelSnapshot) -> Guidance:
        gaps = [
            room
            for room, _ in instances(r for r in snapshot.rooms if re.fullmatch(self.gap, preset_name(r.preset)))
            if room.variant in self.gap_variants
        ]
        named: dict[Exit, Room] = {}
        unknown = []
        for room in gaps:
            exit_ = next((e for e in self.exits if e.area in room.leads_to and e not in named), None)
            if exit_ is None:
                unknown.append(room)
            else:
                named[exit_] = room
        unseen = [e for e in self.exits if e not in named]
        if len(unknown) == 1 and len(unseen) == 1:
            named[unseen[0]] = unknown.pop()
        pois = [Poi(e.label, named[e], e.kind) for e in self.exits if e in named]
        pois += [Poi('Exit', room, 'exit') for room in unknown]
        rest = super().guide(snapshot)
        return Guidance((*pois, *rest.pois), rest.problems)
