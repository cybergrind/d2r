"""The zone graph: a terror zone's levels as a forest rooted at waypoint levels, each level with its parent, its
children, the way in from the parent and the way back up (macros/zone-nav-plan.md §2). Pure data; no game reads.

The player, ~09:20 on 2026-10-21: "I think we need some global (zone level navigation system) and zone level goals
(like `fully_explored`) / so, if we get into one smaller level, we will return back to global level, explore it further
and clear smaller dungeons (all, if there are many)".

- The roots and what each owns come from the zone's catalogue trips (`Chain`, one per routes/tz_routes.py excursion,
  in the itinerary's order: an act script's order, the boss first): a trip's waypoint is a root, each later level's
  parent the level before it on the trip (a toured level's, the tour's hub). The first trip to name a level owns it.
- The marks: a catalogue stage between the two levels (`enter`, `back`, `use`, a `tour`) names its mark; else the
  level's handler's mark named after the level it leads into (or its one 'previous' mark, Sewers 1's 'Way up', for the
  way back); else the generic way out levels/exits.py marks every warp and border with (`short_name`). `Way.source`
  says which, so the unconfirmed ones can be logged (stage 0).
- The way back exists when the static links (levels.txt Vis slots, `presets.LEVEL_LINKS`, both directions) or a
  border join the two levels; a level entered only by a portal (the Arcane Sanctuary, Tristram) has none.
- A tour's levels (the Canyon of the Magi's seven tombs, routes/model.py `tour`) are its hub's children, `toured`:
  which of the hub's marks leads into which is not known, so the hub goes into the nearest not yet gone through.
- A tour's side level (Duriel's Lair, levels/handlers/tal_rasha.py DURIEL): a level after the tour that every toured
  level leads into by a `use` stage (the Orifice's portal). It hangs under the hub (`side`, `sources` the toured
  levels), is never gone into from the hub, only by the toured level whose mark exists (the others report it absent:
  routes/progress.py `done`), and has no way back (a portal: the Town Portal out).
- `bordering`: the levels walked or stepped into from a level with no town between (stage 3's walk from root to root,
  macros/zonenav.py `walk_to`): the static links, routes/links.py BORDERS and the outdoor handlers' named exits.
"""

import functools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from inventory_tracking.levels.exits import short_name
from inventory_tracking.levels.presets import display_name, open_passage
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.links import linked
from inventory_tracking.routes.model import USE


# How a way is taken: a warp is a door or stairs (a press, macros/teleport.py `walk_into`); a walk crosses an open
# passage or a border (pursuit.py `through`, `carried`); a portal goes one way (a `use` stage: no way back by it)
WARP, WALK, PORTAL = 'warp', 'walk', 'portal'
# Where a way's mark comes from: the catalogue's stage, the level's handler, or the generic way out (levels/exits.py)
CATALOGUE, HANDLER, GENERIC = 'catalogue', 'handler', 'generic'


@dataclass(frozen=True)
class Way:
    """How level `source_area` is left for level `to`: by the mark labelled `mark`, of `kind`, named by `source`."""

    to: int
    mark: str
    kind: str
    source: str


@dataclass(frozen=True)
class Chain:
    """One catalogue trip as the graph reads it (macros/tzroutine.py `Excursion`): `areas` from the waypoint on;
    `worked` the terrorized ones; a tour's `hub` and `tours`; `passes` the levels crossed to the boss (worked after)."""

    waypoint: int
    areas: tuple[int, ...]
    worked: frozenset[int] = frozenset()
    hub: int | None = None
    tours: tuple[int, ...] = ()
    passes: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Node:
    """A level of the zone: `root` the waypoint level its trips start at; `parent` None for a root; `children` in the
    trips' order; `entry` the way in from the parent; `back` the way up to it (None: a portal level, or a root);
    `worked` False for a level only crossed (not terrorized); `crossed` a level crossed to the boss, worked after it;
    `boss` the end of a trip that crossed levels to its boss (the Chaos Sanctuary, the Worldstone Chamber); `toured`
    a tour's level, entered by the nearest of its hub's marks not yet gone through (the Canyon's tombs); `side` a
    tour's side level, entered by a `use` stage of one of `sources` (Duriel's Lair by the true tomb's Orifice)."""

    area: int
    root: int
    parent: int | None = None
    children: tuple[int, ...] = ()
    entry: Way | None = None
    back: Way | None = None
    worked: bool = True
    crossed: bool = False
    boss: bool = False
    toured: bool = False
    side: bool = False
    sources: tuple[int, ...] = ()


@dataclass(frozen=True)
class ZoneGraph:
    """The zone `zone`: its `roots` in play order and every level's `Node`."""

    zone: str
    roots: tuple[int, ...]
    nodes: Mapping[int, Node] = field(hash=False, compare=False)

    def node(self, area: int | None) -> Node | None:
        return self.nodes.get(area) if area is not None else None

    def depth(self, area: int) -> int:
        """Floors from `area` down to the deepest level under it, itself counted: 1 for a level with no children."""
        node = self.nodes[area]
        return 1 + max((self.depth(child) for child in node.children), default=0)

    def subtree(self, area: int) -> tuple[int, ...]:
        """`area` and every level under it, depth first in the children's order."""
        node = self.nodes[area]
        return (area, *(level for child in node.children for level in self.subtree(child)))

    def ancestors(self, area: int) -> tuple[int, ...]:
        """The levels above `area`, its parent first, its root last."""
        found: list[int] = []
        node = self.nodes[area]
        while node.parent is not None:
            found.append(node.parent)
            node = self.nodes[node.parent]
        return tuple(found)

    def said(self) -> str:
        """The graph as the log says it: `81 (96, 97, 82 (98, 99)); 80 (...)`."""

        def tree(area: int) -> str:
            node = self.nodes[area]
            inner = ', '.join(tree(child) for child in node.children)
            return f'{area} ({inner})' if inner else str(area)

        return '; '.join(tree(root) for root in self.roots)

    def unconfirmed(self) -> tuple[str, ...]:
        """The ways no catalogue stage or handler names (the generic mark, levels/exits.py), and the levels with no
        way back: what stage 0's log asks the game to confirm."""
        found = []
        for node in self.nodes.values():
            if node.parent is None:
                continue
            if node.entry is not None and node.entry.source == GENERIC:
                found.append(f'{node.parent}->{node.area} {node.entry.mark!r}')
            if node.back is None:
                found.append(f'{node.area}->{node.parent} none')
            elif node.back.source == GENERIC:
                found.append(f'{node.area}->{node.parent} {node.back.mark!r}')
        return tuple(found)


def zone_graph(zone: str, chains: Sequence[Chain]) -> ZoneGraph:
    """The zone's graph from its trips in play order (`Chain`): each new waypoint a root, each level's parent the one
    before it on the first trip to name it (a toured level's, the hub)."""
    roots: list[int] = []
    parents: dict[int, int | None] = {}
    owner: dict[int, int] = {}
    worked: set[int] = set()
    crossed: set[int] = set()
    bosses: set[int] = set()
    toured: set[int] = set()
    sides: dict[int, tuple[int, ...]] = {}
    order: dict[int, list[int]] = {}
    for chain in chains:
        worked |= chain.worked
        crossed |= chain.passes
        if chain.passes:
            bosses.add(chain.areas[-1])
        if chain.waypoint not in parents:
            roots.append(chain.waypoint)
            parents[chain.waypoint] = None
            owner[chain.waypoint] = chain.waypoint
        before = chain.waypoint
        side = side_levels(chain)
        for area in chain.areas[1:]:
            parent = chain.hub if area in chain.tours and chain.hub is not None else before
            if area in side and chain.hub is not None:
                parent = chain.hub
                sides.setdefault(area, chain.tours)
            if area not in parents:
                if area in chain.tours and chain.hub is not None:
                    toured.add(area)
                parents[area] = parent
                owner[area] = owner[parent]
                order.setdefault(parent, []).append(area)
            before = area
    nodes = {}
    for area, parent in parents.items():
        entry = way(parent, area) if parent is not None else None
        back = way(area, parent) if parent is not None and joined(area, parent) else None
        if area in sides:
            entry, back = way(sides[area][0], area), None  # by a toured level's `use`; a portal: no way back
        nodes[area] = Node(
            area,
            owner[area],
            parent,
            tuple(order.get(area, ())),
            entry,
            back,
            worked=area in worked,
            crossed=area in crossed,
            boss=area in bosses,
            toured=area in toured,
            side=area in sides,
            sources=sides.get(area, ()),
        )
    return ZoneGraph(zone, tuple(roots), nodes)


def side_levels(chain: Chain) -> frozenset[int]:
    """The levels of `chain` after its tour that every toured level leads into by a catalogue `use` stage (the
    Orifice's portal into Duriel's Lair from each tomb)."""
    if not chain.tours or chain.hub is None:
        return frozenset()
    last = max(chain.areas.index(level) for level in chain.tours if level in chain.areas)
    return frozenset(area for area in chain.areas[last + 1 :] if all(uses(tour, area) for tour in chain.tours))


def uses(area: int, to: int) -> bool:
    """Whether a catalogue script of level `area` has a `use` stage into level `to`."""
    return any(
        stage.kind == USE and stage.to == to
        for route in ROUTES
        for script in route.scripts
        if script.area == area
        for stage in script.stages
    )


def joined(area: int, to: int) -> bool:
    """Whether level `to` is reached from `area` by a door, stairs or a border (no portal): a way back."""
    return linked(area, to) or linked(to, area)


@functools.cache
def bordering(area: int, to: int) -> bool:
    """Whether level `to` is walked or stepped into from `area` with no town between: a door or stairs of the static
    links, a border of routes/links.py BORDERS, or an outdoor handler's exit named after `to` (levels/handler.py
    `ExitsHandler.exits`: Outer Steppes - Plains of Despair - City of the Damned, Cold Plains - Burial Grounds)."""
    if joined(area, to):
        return True
    for one, other in ((area, to), (to, area)):
        handler = handler_for(one)
        if handler is not None and any(exit_.area == other for exit_ in getattr(handler, 'exits', ())):
            return True
    return False


@functools.cache
def way(area: int, to: int) -> Way:
    """How `area` is left for `to`: the catalogue's stage, else the handler's mark, else the generic way out."""
    kind = WALK if joined(area, to) and open_passage(area, to) else WARP
    for route in ROUTES:
        for script in route.scripts:
            if script.area != area:
                continue
            for stage in script.stages:
                if stage.to == to and stage.mark:
                    return Way(to, stage.mark, PORTAL if stage.kind == USE else kind, CATALOGUE)
                if to in stage.tours:
                    return Way(to, stage.mark, kind, CATALOGUE)
    handler = handler_for(area)
    if handler is not None:
        names = {short_name(to), display_name(to)}
        named = next((spec.label for spec in handler.pois if spec.label in names), None)
        if named is None:
            named = next((exit_.label for exit_ in getattr(handler, 'exits', ()) if exit_.area == to), None)
        if named is not None:
            return Way(to, named, kind, HANDLER)
        previous = [spec.label for spec in handler.pois if spec.kind == 'previous']
        if to < area and len(set(previous)) == 1:
            return Way(to, previous[0], kind, HANDLER)  # Sewers 1's 'Way up' (which ladder leads where isn't known)
    return Way(to, short_name(to), kind, GENERIC)
