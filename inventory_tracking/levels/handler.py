"""Handler building blocks: a level handler file declares HANDLERS with these helpers.

A POI spec is a full-match regex over LvlPrest names, never one Def: boss and stairs rooms exist once per
doorway orientation (Arcane Summoner N/S/E/W = 525-528). A required POI matching no room or several is a
problem to log, never guessed; optional POIs (waypoints) are silent when absent. Chunks of one large preset
(8x8 Room2s sharing its bounds) count as one match covering the whole preset. `sides`, `at`, `boss` and
`thing` place the POI inside the preset (see PoiSpec). Logic that fits no pattern subclasses Handler.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace

from inventory_tracking.levels.model import CLICKED, Guidance, LevelSnapshot, Poi, Room
from inventory_tracking.levels.presets import object_spots, preset_name
from inventory_tracking.levels.spots import pinpoint
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror import elites


@dataclass(frozen=True)
class PoiSpec:
    label: str
    pattern: str
    kind: str = 'target'
    optional: bool = False
    family: str | None = None  # every matching preset name must start with it (checked offline)
    sides: tuple[str, ...] = ()  # per DS1 variant (File1.. order): 'N'/'S'/'E'/'W' edge holding the POI, north = -y
    inset: float | None = None  # how far inside that edge (fraction of the preset); None = SIDE_INSET
    variants: tuple[int, ...] = ()  # only these DS1 variants (file index) match; empty = any
    each: bool = False  # mark every matching instance (none is fine), e.g. Lower Kurast's camps
    warp: bool = False  # an entrance of another kind (a side trip as 'target'): mark its warp tile too
    boss: str = ''  # the POI is where the preset's DS1 file places this super unique (terror/elites.py)
    at: tuple[float, float] | None = None  # a one-layout preset: the POI this far (world units) from its origin
    at_in: tuple[tuple[str, tuple[float, float]], ...] = ()  # `at` by preset name (the Summoner's four arms)
    stand: tuple[int, int] = (0, 0)  # tiles from the `sides` spot to where the mark goes: a place to fight from
    use: int = 0  # objects.txt id of an object near the POI the step clicks (levels/model.py PORTAL)
    thing: int = 0  # objects.txt id of an object the preset's file places: the POI is on it (presets.object_spots)

    def matches(self, name: str) -> bool:
        return re.fullmatch(self.pattern, name) is not None


@dataclass(frozen=True)
class Handler:
    name: str
    areas: frozenset[int]
    pois: tuple[PoiSpec, ...]
    confirmed: bool = False  # True only when a real fixture test replays it

    def labels(self) -> frozenset[str]:
        """Every label this handler can give a mark: what a route's stage may name (routes/check.py)."""
        return frozenset(spec.label for spec in self.pois)

    def spec(self, label: str) -> PoiSpec | None:
        return next((spec for spec in self.pois if spec.label == label), None)

    def guide(self, snapshot: LevelSnapshot) -> Guidance:
        pois, problems, absent = [], [], set()
        for spec in self.pois:
            start = len(pois)
            groups = instances(room for room in snapshot.rooms if spec.matches(preset_name(room.preset)))
            if spec.variants:
                groups = [group for group in groups if group[0].variant in spec.variants]
            found = [room for room, _ in groups]
            if spec.each and spec.thing:
                pois.extend(poi for room in found for poi in thing_pois(spec, room))
                # The client holds every room from entry: every layout read and no mark = none (lower-kurast-plan.md).
                named = instances(room for room in snapshot.rooms if spec.matches(preset_name(room.preset)))
                if len(pois) == start and all(room.variant is not None for room, _ in named):
                    absent.add(spec.label)
            elif spec.each:
                pois.extend(Poi(spec.label, room, spec.kind) for room in found)
            elif len(found) == 1 and spec.thing:
                room = found[0]
                spots = thing_pois(spec, room)
                if spots and len(spots) == 1:
                    pois.extend(spots)
                elif room.variant is None and not whole_level_around(groups[0], snapshot):
                    pois.append(Poi(spec.label, room, spec.kind))  # the room for now: its layout is read near it
                elif room.variant is None:
                    problems.append(f'{spec.label}: layout variant unknown')
                elif len(spots) != 1:
                    problems.append(
                        f'{spec.label}: the layout (variant {room.variant}) places {len(spots)} of object {spec.thing}'
                    )
                else:
                    pois.extend(spots)
            elif len(found) == 1 and spec.sides:
                room = found[0]
                if room.variant is None or room.variant >= len(spec.sides):
                    problems.append(f'{spec.label}: layout variant unknown')
                else:
                    side = spec.sides[room.variant]
                    inset = SIDE_INSET if spec.inset is None else spec.inset
                    spot = side_room(room, side, inset)
                    spot = replace(spot, x=spot.x + spec.stand[0], y=spot.y + spec.stand[1])
                    pois.append(Poi(spec.label, spot, spec.kind))
            elif len(found) == 1 and (spec.at or dict(spec.at_in).get(preset_name(found[0].preset))) is not None:
                room = found[0]
                at = spec.at or dict(spec.at_in)[preset_name(room.preset)]
                pois.append(
                    Poi(
                        spec.label,
                        marker_room(room, room.x + at[0] / TILE_UNITS, room.y + at[1] / TILE_UNITS),
                        spec.kind,
                    )
                )
            elif len(found) == 1 and spec.boss:
                room = boss_room(found[0], spec.boss)
                if room is None:
                    problems.append(f'{spec.label}: {spec.boss} is not in the layout (variant {found[0].variant})')
                else:
                    pois.append(Poi(spec.label, room, spec.kind))
            elif len(found) == 1 and whole_level_around(groups[0], snapshot):
                # A whole-level layout the player stands in gives no direction; a smaller one is "here".
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
            if spec.use:
                pois[start:] = [replace(poi, use=spec.use) for poi in pois[start:]]
        return Guidance(tuple(pois), tuple(problems), frozenset(absent))


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
                if found[key][0].variant is None and room.variant is not None:
                    # Layouts are read chunk by chunk as rooms load: any chunk's reading is the preset's.
                    found[key][0] = replace(found[key][0], variant=room.variant)
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
    return marker_room(room, room.x + room.width * fx, room.y + room.height * fy)


def marker_room(room: Room, x: float, y: float) -> Room:
    """An 8x8 marker room of `room`'s preset centred on a tile point."""
    # The block keeps the preset's origin, so a warp spot (levels/spots.py) still finds its tile.
    block = room.block or (room.x, room.y, room.width, room.height)
    return Room(room.preset, round(x) - 4, round(y) - 4, 8, 8, room.variant, block)


def thing_pois(spec: PoiSpec, room: Room) -> list[Poi]:
    """A POI on each object of `spec.thing` that `room`'s layout places; none when the layout is unread."""
    return [
        Poi(
            spec.label,
            marker_room(room, room.x + x / TILE_UNITS, room.y + y / TILE_UNITS),
            spec.kind,
            spot=(room.x + x / TILE_UNITS, room.y + y / TILE_UNITS),
            use=spec.thing if spec.thing in CLICKED else 0,
        )
        for x, y in object_spots(room.preset, room.variant, spec.thing)
    ]


def boss_room(room: Room, name: str) -> Room | None:
    """A marker room on the super unique `name` as `room`'s DS1 file places it; None if unread or absent."""
    if room.variant is None:
        return None
    spots = [
        (x, y)
        for kind, found, x, y in elites.table().presets.get((room.preset, room.variant), ())
        if kind == 'super' and found == name
    ]
    if len(spots) != 1:
        return None
    ((x, y),) = spots
    return marker_room(room, room.x + x / TILE_UNITS, room.y + y / TILE_UNITS)


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
    boss: str = '',
    at: tuple[float, float] | None = None,
    stand: tuple[int, int] = (0, 0),
    at_in: dict[str, tuple[float, float]] | None = None,
    use: int = 0,
    thing: int = 0,
) -> Handler:
    """One POI: the unique room (or preset instance) whose preset name fully matches `preset`.

    kind='stairs' when the target leads to the next level (an entrance or an exit quadrant).
    """
    spec = PoiSpec(
        label, preset, kind, sides=tuple(sides), inset=inset, boss=boss, at=at, stand=stand,
        at_in=tuple((at_in or {}).items()), use=use, thing=thing,
    )  # fmt: skip
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


# Act 1 border presets whose open DS1 files (Bord*o.ds1 = 3, Bord*oe.ds1 = 4) are the walkable gaps
# between levels (D2MOO DrlgOutPlace).
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
    """Outdoor level: every open border gap is a POI, before the `pois` specs unless `pois_first`.

    A gap is named by the level behind it (Room.leads_to, read once the player was near); the last unknown gap
    takes the last unseen exit by elimination; others are plain 'Exit'. Missing or extra gaps are no problem.
    """

    exits: tuple[Exit, ...] = ()
    gap: str = ACT1_GAP
    gap_variants: tuple[int, ...] = (3, 4)
    pois_first: bool = False

    def labels(self) -> frozenset[str]:
        return super().labels() | {exit_.label for exit_ in self.exits}

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
        pois = [Poi(e.label, named[e], e.kind, area=e.area) for e in self.exits if e in named]
        pois += [Poi('Exit', room, 'exit') for room in unknown]
        rest = super().guide(snapshot)
        order = (*rest.pois, *pois) if self.pois_first else (*pois, *rest.pois)
        return Guidance(order, rest.problems, rest.absent)
