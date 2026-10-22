"""The teleport step: one step toward the level card's mark, a teleport as far as the screen allows or, at the
door to the next level, a walk into it. The history of each rule is in macros/plan.md.

The mark is the first one on the card (levels/guide.py `target`). Teleport is found, not assumed:
skill 54 in a skill slot gives the key (skills.py); a staff with Teleport charges in either weapon
set says whether to swap first and how many charges are left. Without a staff the key is pressed as
it is (an oskill) and the character moving is the proof. The staff is left in hand afterwards: the
next press needs it too.

The step is asked for again and again: the pointer flicks rather than glides, nothing
waits at the end, the mouse may drift under the player's hand (POINTER_DRIFT), and a press during a
step queues one more step (runner).

A hop lands on the footing in view that leaves the shortest way to go (`landing`). Footing is the
loaded rooms' walkable sub-tiles where they were read (the spot and its neighbours a world unit
around, `footing`); the room rectangle stands in where no grid was read. The way to go is a
potential over landable tiles (`Way`): Dijkstra from the mark's tile, each step a hop of at most
REACH_TILES, walls in between or not, cached per target. The mark itself is a candidate, so the last
hop lands on it. Each hop logs where it aimed and where the character landed.

A door is clicked, not teleported onto: a teleport onto a warp tile does not take it, walking into it
does. The game walks a clicked character to one spot beside the stairs before the level changes; that
spot is remembered per door (`Entries`), the last hop lands on it, and the click from there is the
step in. A door with no spot known yet is clicked from within NEAR_WARP, after a hop beside it
(`approaches`). The click goes to the ground at the warp tiles first and to the doorway drawn above
them next (DOOR_AIMS).
"""

import heapq
import json
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.common import LOG
from inventory_tracking.game.decode import containers
from inventory_tracking.game.layout import BANK, ITEM_UNIT, MONSTER_UNIT, NO_OWNER, OBJECT_UNIT, TILE_UNIT
from inventory_tracking.game.records import Player, Thing, Warp, World
from inventory_tracking.game.view import CORNER_BOTTOM, UNIT_PIXELS, VIEW, Viewport
from inventory_tracking.levels.doors import door_sizes
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import (
    ARCANE_PORTAL,
    DURIEL_PORTAL,
    HELL_GATE,
    PORTAL,
    SEALS,
    SUPER_CHEST,
    THRONE_PORTAL,
    TOWN_PORTAL,
    UNIQUE_CHEST,
    WIRTS_BODY,
    Ground,
    Target,
)
from inventory_tracking.levels.presets import warp_box
from inventory_tracking.levels.route import Point, room_at
from inventory_tracking.macros.act import until
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Build
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, press_skill, settle, swap_until, world_point
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.targeting import (
    CLICK,
    EMPTY,
    WAIT,
    door_hover,
    entry_learnable,
    nearest_warp,
    nothing_under,
    object_door,
)
from inventory_tracking.native.layout import TILE_UNITS


# World units: a door this close is walked into, not teleported next to (from 20 the character
# walked around a wall for six seconds).
NEAR_WARP = 10.0
# The last hop before a door with no remembered spot lands beside it, not on it: spots APPROACH units
# from the warp's centre, a tile beyond its own tiles, the nearest to the character among those with
# footing. Nothing nearer than WARP_TILES to the centre is landed on.
APPROACH = 6.5
WARP_TILES = 5.0
BEARINGS = 16
WALKING = frozenset((2, 3, 6))  # the character's modes while it goes somewhere on foot (combat/policy.py RUN_MODES)
READY_SECONDS = 2.5  # for the cast before to end, as a skill's key waits (routines.py `press_skill`)
SETTLE_SECONDS = 0.5  # for a walk to end before a hop is planned from where the character stands
MOVED = 2.0  # world units the character must have moved for a teleport or a walk to count
# World units from a spot that is not a door: the character is there. A hop onto the spot itself lands beside it or
# not at all when a monster stands on it (Nihlathak on his: no move from 3.5 away at 12:56:41 on 2026-10-11).
SPOT_NEAR = 5.0  # one tile, as the route scenarios count an arrival (scenarios/navigation/harness.py ARRIVE)
HOP_SECONDS = 1.5  # a teleport resolves well within this
WALK_SECONDS = 1.5  # the first step of a walk
# Where a door is clicked, in classic pixels (600 high; across, down) from the ground at the centre
# of its warp tiles, tried in turn until the level changes. The ground takes the doors of the
# Catacombs and the Jail and none in the Worldstone Keep. lvlwarp.txt has why: a door takes clicks in a box around its
# picture, which reaches 30 pixels below the tile for 'Act 1 Catacombs Down' and 5 for 'Act 5 Baal
# Temple Down', 110 above for both. The side aims are for a box that sits left or right of the
# tiles' centre (the Baal boxes are 95 and 80 wide, the two tiles 160); which tile the box hangs
# from is not known here.
DOOR_AIMS = ((0, 0), (0, -45), (-50, -45), (50, -45))
DOOR_SECONDS = 1.2  # a click on a door at most NEAR_WARP away, then the new level: 0.2 to 0.35 s in the log
# The aim that takes a door, by `Entries.key`, where the saved logs say: tried first. A door's box hangs
# from its picture, so the aim goes with the preset, not the level. Tower Cellar 1-3 (host, 20:05 on
# 2026-10-10): the stairs down took (-50, -45) in each of the W, E and N presets, after 1.4 s lost on
# each of the two aims before it; S is taken to be the same. The Forgotten Tower in Black Marsh took
# (-50, -45) four times on 2026-10-10 and missed it twice, (0, -45) once of three, (0, 0) never: all
# guesses round a box that is 42 to 122 pixels above the tiles. The door's own box (`box_aim`) goes
# before these, and a door learnt since (`AIMS`) next.
KNOWN_AIMS = {
    'preset 143:stairs': (-50, -45),
    'preset 144:stairs': (-50, -45),
    'preset 145:stairs': (-50, -45),
    'preset 146:stairs': (-50, -45),
    'preset 163:stairs': (-50, -45),
}
DEFAULT_AIMS = Path('inventory_tracking/runs/macros/door-aims.json')
# Where the character stood when a door took it, relative to the warp point the level card marks (world
# units), remembered per door and kept across games: the game walks a clicked character to one spot beside
# the stairs before the level changes (the Catacombs: 3 units "south" of the mark, round a block of walls
# the mark sits in). The last hop lands on that spot, and the click from there is the step in.
DEFAULT_ENTRIES = Path('inventory_tracking/runs/macros/door-entries.json')
ENTRY_MAX = 6.0  # world units from the mark: a last position further off is not the door's own spot
# Entry spots known before any is learnt, by `Entries.door_key` (world units from the mark). Two doors of one preset
# share its key (the Burial Grounds' Crypt and Mausoleum: 'preset 108:stairs'), so each door has its own row, looked up
# before the preset's (`Entries.offset`). The Crypt's mark and warp unit stand inside the tomb's walls, closed on the
# south and west: with no spot the level run ended on the south face, 5.7 units from the unit, and no click took
# ("no click took Crypt" x4, 08:01-08:07 on 2026-10-21, the game left each time; rca/2026-10-21/crypt-door-findings.md
# §2, §5). The spots are on the open east side: the player's own Crypt entries of 2026-10-17 took from mark + (6, -2);
# the Mausoleum's one hand entry from + (5, +1), its grid open east. Checked on the four takes' grids: on footing, 3.5
# to 3.6 units from the unit. A door's first entry learns its own row, which goes before its seed.
KNOWN_ENTRIES: dict[str, tuple[float, float]] = {
    'preset 108:stairs:Crypt': (6.0, -1.5),
    'preset 108:stairs:Mausoleum': (6.0, 0.0),
    # Flayer Dungeon 1 from the Flayer Jungle: the level changed at (-9, -7) from the mark in 7 entries out of 7 on
    # 2026-10-19/20, each after a first click that walked 6 units and stopped (targeting-findings.md §1.1)
    'preset 602:stairs:Flayer Dungeon 1': (-9.0, -7.0),
}
# False: no seeded spots (KNOWN_ENTRIES), a door with nothing learnt is gone for by its mark as before (2026-10-21, "no
# click took Crypt" x4). The doors' own rows are learnt and read either way
DOOR_SEEDS = True
# World units: the remembered spot this near over open ground is walked to by the click on the door, not
# hopped onto (user, 2026-10-10: "we have jumped twice around the entrance": a hop beside the door, a
# hop onto the spot 6 units on, then the click).
ENTRY_WALK = 9.0
ENTRY_NEAR = 4.0  # world units from the remembered spot: near enough to click the door from
# World units a click walked the character before the level changed: under this the spot clicked from is the door's
# own (no step at all, history-through-2026-10-12.md: the Tower Cellar). A spot the click walked on from was learned
# as proven and hopped onto again and again, each time walking 5-6 units round the Catacombs stairs' block of walls
# (preset 292's +2, -2 from 11:10 to 11:52 on 2026-10-18, rca/2026-10-18/stairs-walks-findings.md)
NO_WALK = 0.5
# World units of a walk round to the remembered spot from within NEAR_WARP of the mark that the click makes instead
# of a hop onto it: a walk of 8 costs ~0.2 s, a hop 0.37 s (the same findings, §5 C)
ENTRY_AROUND = 8.0
# World units from the remembered spot to where the character stands to click the door (`entry_stand`): a spot a hop
# is aimed at only where it has footing (`landing`). A spot learned beside a wall had none (the Catacombs stairs:
# -2.5, +1.9 from the mark, a corner of the block of walls one unit off), so the level run's last hop landed on the
# footing nearest the way's tile, LOOP_SHORT back toward the character (13:00-13:10 on 2026-10-18: east of the block
# 2 to 7.6 units off, the click walking round it in 21 of 27 doors). The footing within this of the spot is a click
# without a walk too: the spots from which the click walked nothing lie 4.6 units around the door unit, 3.5 west of
# the mark (rca/2026-10-18/stairs-walks-findings.md §2).
STAND_SNAP = 2.0
WALK_POLL = 0.04  # seconds between looks while the character walks into a door (one game frame)
LOST_KEY = (
    'Teleport is off its key: bind it again (the skill list, the pointer on Teleport, the key). '
    'It is lost when a game is left with the staff in hand'
)
# A press the game drops: Worldstone Keep 3, 03:12:00 on 2026-10-11, the 21st hop of a chain (the
# request pressed six times in 1.5 s) cast nothing, was waited for HOP_SECONDS and named as the lost
# key; the same aim landed 0.5 s later. A hop lands 0.31 s after its key at the median, so with the
# staff in hand and no charge spent after REPRESS_SECONDS the key is pressed once more. The lost key
# is named only in a game no hop has landed in yet (`LANDED`).
REPRESS_SECONDS = 0.6
LANDED: list[str] = []  # the game the last hop landed in
# Where and when the last hop was seen to land. The next hop is planned and aimed from there at once,
# during the rest of that cast: the key itself waits for the cast's end (routines.press_skill). The
# game moves the character 283 ms after the key and ends the cast at 388 ms (3,300 hops recorded on
# 2026-10-11), and the next key went down 567 ms after the one before: 180 ms of every hop were the
# wait for the cast's end before the planning and the pointer's move.
LANDING: list[tuple[float, float, float]] = []
# 2026-10-21: the last hop that landed MOVED or more off its aim, as (aim, landing, area): a hop aimed there again
# from that landing moved nothing in 33 of 48 such hops within 10 units (hunting/moves.py REHOP_WALK reads it).
MISSED: list[tuple[Point, Point, int]] = []
REHOP_SAME = 1.5  # world units between two aims that are the same spot
# 2026-10-21: Teleport the character's own (no staff read) is pressed again too when nothing landed REPRESS_SECONDS
# after the key and the character stands free where it was. 55 of 151 own hops that ran out their act on 2026-10-20/21
# had cast and moved nothing (the server's refusal, rca/2026-10-17/teleport-not-cast-findings.md: a re-press lands),
# 16 more had cast nothing; the re-press was the staff's only. Off: the staff's re-press only, as before.
OWN_REPRESS = True
# 2026-10-21: modes in which the game drops a Teleport key instead of keeping it for the end of what the character
# does: 9 (a block; 25 of 25 such keys cast nothing on 2026-10-20/21) and 4 (a hit, 1 of 1). The key waits for the
# mode's end, KEY_DROP_SECONDS at most. Off: pressed at once, as before (rca/2026-10-21/priced-act-expired-findings.md).
KEY_DROP_WAIT = True
KEY_DROP_MODES = frozenset((4, 9))
KEY_DROP_SECONDS = 0.6
HOP_POLL = 0.01  # seconds between looks for a hop's landing and its cast's end (30 ms otherwise, engine.POLL)
# Seconds after the cast before is over within which a kept key's cast shows (the game issues it on its
# next frame, or the one after when the press sat in its second entry).
QUEUED_SECONDS = 0.09
LANDING_FRESH = 0.6  # seconds a landing stands for where the character is, if it is still there
HOVER_SECONDS = 0.06  # for the game to note what is under the pointer after it moved (a frame or two)
# Unit types of the record of the unit under the pointer that are not a door: a monster (the mercenary
# and the summons land beside the character after a hop), an item. An aim with one of them under it is
# left for last: the click would go to that unit.
IN_THE_WAY = frozenset((MONSTER_UNIT, ITEM_UNIT))
# A door is a warp tile (TILE_UNIT) in that record. In the logs to 2026-10-10 each of the 31 clicks
# a door took had a tile in the record, and none of the 4 made with an object in it took: those were
# clicks on the ground, each walking the character off for 1.4 s (the tower's door in Black Marsh,
# host, 22:43 on 2026-10-10: 6 s around the entrance). The record keeps the last unit when the pointer
# is on nothing, so a tile in it may be the door just come through: such an aim is clicked as before.
# A click made while a cast ends is swallowed: the character neither walks nor goes in. Tower Cellar,
# host, 23:26 and 23:35 on 2026-10-10: attack mode's strike 0.04 s and 0.7 s before the click on the
# stairs, the character where it stood 1.4 s later, then two aims off the door and 4.8 s in all; the
# same aim from the same spot took in 0.23 s in the next game. So the character is waited free
# (`settle`) and a click that moved nobody is made again, STILL_SECONDS on, before the next aim is tried.
DOOR_CLICKS = 2
# Seconds an object with a panel (`Use.opens`: the stash, a waypoint) is looked at for its panel before the first aim:
# the walk's own last click opened the waypoint's 0.05-0.19 s after the character stopped (14:42:09 and 14:18:25 on
# 2026-10-18; waypoint.py `open_panel` relies on it)
PANEL_GRACE = 0.25
# A character that has not moved this long after a click was not sent anywhere (a door took one in 0.37 s at most).
STILL_SECONDS = 0.5
WARP_NEAR = 12.0  # world units from the mark to its door unit (the tower's in Black Marsh: 7.0)
# Controller mode, a door with no door unit (`pad_door`): the walk goes through the mark DOOR_PAST units on past it,
# from the door's entry spot, onto which it first walks from further than DOOR_LINE.
DOOR_PAST = 3.0
DOOR_LINE = 2.0
# An object the mark names (`Target.use`) is clicked like a door, but it is an object unit, not a warp
# tile: the door code has no place for it and takes an object under the pointer for a miss. Stony Field
# (user, 2026-10-12): the step stood at the Cairn Stones, "At Tristram", and the portal was never taken.
# An aim is clicked only with that object (OBJECT_UNIT) in the game's record of the unit under the pointer.


EXPIRED = 'priced act expired'  # hunting/moves.py `priced_for`'s stop


class Untook(Abort):
    """An object's clicks took nothing: no click took it, or none of its aims had it under the pointer, or it was not
    ready for one (the Throne's portal with Baal on his throne: `baal_gone`). Zone navigation blocks the level such an
    object leads into and goes on (tzloop.py `zone_use`); to every other caller an Abort as before."""


class Covered(Abort):
    """The hands did not make their act because monsters stood where it was to be made: under the
    pointer at every aim on an object, or on the ground a walk was to be clicked at (`units`, their ids).
    An Abort like any other to a caller that only stops; the pursuit loop reads them as what bars its
    goal, and fights them first (macros/goals.py `first_fight`)."""

    def __init__(self, reason: str, units: Iterable[int]) -> None:
        super().__init__(reason)
        self.units = frozenset(units)


@dataclass(frozen=True)
class Use:
    """How an object a mark names is clicked and what shows that it took."""

    aims: tuple[tuple[int, int], ...]  # classic pixels from its ground point, tried in turn
    near: float  # world units from the mark to the object
    leaves: bool  # it took when the level changed; else when the object's mode did
    begun: str  # said before the click
    done: str  # and after it took
    absent: str  # at the mark with no such object shown
    # Seconds after it took within which the game brings what it calls (a seal's boss and pack: first seen
    # 0.95 to 1.02 s after the seal, rca/2026-10-13/situations.md §3, cs-run.md §2): the use is not over
    # before then (the pursuit loop's level run moves nowhere meanwhile: macros/pursuit.py `Facts.settling`).
    brings: float = 0.0
    # objects.txt classes the object at the mark may be: a spot whose class the game rolls (levels/model.py
    # UNIQUE_CHEST). Empty: the mark's own id.
    kinds: frozenset[int] = frozenset()
    # The panel (World.open_panels) whose opening says it took, whatever its mode: a waypoint (macros/waypoint.py).
    # Empty: `leaves` says.
    opens: str = ''
    # The object may be gone (a chest another player opened, a spot the game left empty): with the character at the
    # mark and none shown, the mark is done with (route.note_empty; the player, 2026-10-16). False: none shown is a
    # read that missed it (a seal is never gone), and the step stops saying so.
    gone: bool = False


def classes(use: int) -> frozenset[int]:
    """The objects.txt classes an object a mark names (`Target.use`, a USES key) may be."""
    return USES[use].kinds or frozenset((use,))


CHEST_AIMS = ((0, -10), (0, 0), (0, -22), (12, -10), (-12, -10), (0, -36))
# A portal's aims down its middle, then its top and its sides: a Doom Ape killed on the portal at 05:25:08 on
# 2026-10-18 lay under all three of the middle's, and the game was left for it
PORTAL_AIMS = ((0, -45), (0, -75), (0, -15), (0, -95), (30, -60), (-30, -60), (30, -25), (-30, -25))
SUMMONING_SEALS = (392, 394, 396)  # DiabloSeal1, 3, 5: the Infector's, De Seis's, the Vizier's (levels/model.py SEALS)
SEAL_BRINGS = 1.2  # seconds: the seal's pack was first seen 0.95 to 1.02 s after it opened, with a frame to spare
# Seconds a chest's drops take to show after it shows opened: none to speak of. In the takes of 2026-10-15 21:08-21:28
# (Lower Kurast, 13 chests of classes 181 and 183 opened by the player's click with something on the ground after),
# every first drop was in the same read as the chest's mode leaving 0 (the recorder reads both every 0.2 s,
# record.py SLOW_SECONDS); drops seen later near it were the next chest's. One read and a little more, so the look
# after the click sees what fell before the run goes on to the next chest. The macro's own reads saw the drops 14 ms
# after the open (01:38:04.042 -> .056 on 2026-10-17, rca/2026-10-17/movement-findings.md §4 #4): 0.1 s, not the
# recorder's read and more (0.25 s, about 1 s a game over seven containers).
CHEST_BRINGS = 0.1
USES = {
    # objects.txt's click box of PortalPermanent: 80 pixels wide round its ground point, from 100 above it
    # to 10 below; the aims go down its middle, then its top and its sides (PORTAL_AIMS). The stones' map piece is 40
    # units across, the mark its middle.
    PORTAL: Use(
        PORTAL_AIMS, 40.0, True,
        'Through the portal to {}', '{}: there', 'no portal to {} is open here',
    ),
    # TownPortal has the same box (objects.txt); it is no mark's: the one the cast opened is clicked
    # (macros/portal.py), so `near` is never asked of it.
    TOWN_PORTAL: Use(
        PORTAL_AIMS, 40.0, True,
        'Through the portal to {}', '{}: there', 'no portal to {} is open here',
    ),
    # A waypoint: objects.txt gives it no box (Left..Height 0), so it is taken by its picture, a disc on its ground
    # point (Selectable0 and 2: before and after its first use). The click walks the character there and opens the
    # panel. The aims are a guess round that point, each clicked only with the waypoint under the pointer.
    **{
        kind: Use(
            ((0, 0), (0, -10), (20, -5), (-20, -5)), 15.0, False,
            'Opening {}', '{}: opened', 'no waypoint at {}', opens='waypoint',
        )
        for kind in WAYPOINT_CLASSES
    },
    # The stash (objects.txt `Bank`: no box, Selectable0 only): taken by its picture, a chest on its ground point, as
    # a chest is. The click walks the character there and opens the stash and the inventory (macros/stash.py).
    BANK: Use(CHEST_AIMS, 15.0, False, 'Opening {}', '{}: opened', 'no stash at {}', opens='stash'),
    # objects.txt gives the body no box: it is taken by its picture, which lies on its ground point. It can
    # be searched once (Selectable0 only): mode 0 until then.
    WIRTS_BODY: Use(
        ((0, 0), (0, -8), (12, -4), (-12, -4)), 15.0, False,
        'Searching {}', '{}: searched', '{} is not here',
    ),
    # The red portal on Mephisto's bridge: objects.txt's box is 80 pixels wide round its ground point and
    # 80 high above it. Not seen clicked by the step yet (levels/routes.md, Phase 4).
    HELL_GATE: Use(
        ((0, -40), (0, -65), (0, -15)), 10.0, True,
        'Through {}', '{}: there', '{} is not open here',
    ),
    # The portal into Duriel's Lair beside the true tomb's Orifice, the mark (13 units west and 3 south of it, D2MOO
    # A2Q6.cpp): objects.txt's box is 80 pixels wide round its ground point and 80 high above it, as the red portal's.
    # Not clicked by the step yet (levels/handlers/tal_rasha.py DURIEL, 2026-10-21)
    DURIEL_PORTAL: Use(
        ((0, -40), (0, -65), (0, -15)), 20.0, True,
        'Through the portal to {}', '{}: there', 'no portal to {} is here',
    ),
    # The portal to the Arcane Sanctuary in Palace Cellar 3: objects.txt's box is 60 pixels wide round its
    # ground point and 80 high above it. Not seen clicked by the step yet (routes.md, Phase 6).
    ARCANE_PORTAL: Use(
        ((0, -40), (0, -65), (0, -15)), 10.0, True,
        'Through the portal to {}', '{}: there', 'no portal to {} is here',
    ),
    # The portal Baal leaves the Throne of Destruction by (FinalPortal), into the Worldstone Chamber: objects.txt gives
    # it no box, so it is taken by its picture, standing on its ground point (the mark, wthrone.ds1's (15090, 5005)), by
    # the permanent portals' aims. The player's four entries (takes of 2026-10-11 00:12 and 00:18, 10-14 16:37, 10-17
    # 20:49; rca/2026-10-20/throne-waves-findings.md §5): the clicks that took were (+11, -26), (-36, -61), (-14, -31)
    # and (-1, -49) pixels from its ground point, the last two with the game's hover record naming an object (the
    # portal: no other object class was read there); PORTAL_AIMS' first, (0, -45), is among them. A click walks the
    # character to 3.4-3.9 units south of the ground point, (15090, 5008.5), and the level changed 0.12 s after it
    # stopped (from 6.6 and 7.1 away), or not in 0.8 s and then at a second click from there (10-14, from 12 away):
    # `use_thing`'s next aim from where it stands.
    # Clicks at (-147, +85) and (-159, +87) were ground (a walk, no portal). Not yet clicked by the step (the player,
    # 2026-10-20: "tz leveling should do baal and trone fight"; macros/hunting/throne.py)
    THRONE_PORTAL: Use(
        PORTAL_AIMS, 10.0, True,
        'Through the portal to {}', '{}: there', 'no portal to {} is open here',
    ),
    # The glowing chest, where the game's files place it (the mark is on it). The aims are the ones that
    # opened the two on the host on 2026-10-12 (macros/opening.py AIMS), each by the first.
    SUPER_CHEST: Use(
        CHEST_AIMS, 10.0, False, 'Opening {}', '{}: opened', '{} is not here', brings=CHEST_BRINGS, gone=True
    ),
    # A chest the game rolls at a placed spot (Lower Kurast's camp): opened as the glowing one is, whichever
    # container it is (the player, 2026-10-16: "in LK superchests are looking just like regular chests, so you can
    # just open everything in our target lists"; the camp dumps showed 181 and 183). The pickup key opened such
    # chests in the camp by the same aims.
    UNIQUE_CHEST: Use(
        CHEST_AIMS,
        10.0,
        False,
        'Opening {}',
        '{}: opened',
        '{} is not here',
        brings=CHEST_BRINGS,
        kinds=containers(),
        gone=True,
    ),
    # The Chaos Sanctuary's seals: objects.txt gives them no box (taken by their picture, which stands on
    # their ground point) and one mode they can be clicked in. Not seen clicked by the step yet. The last
    # seal of each arm brings its boss and pack (the take of 12:33 on 2026-10-13: 396, 394, 392).
    **dict.fromkeys(SEALS, Use(CHEST_AIMS, 10.0, False, 'Opening {}', '{}: open', '{} is not here')),
    **dict.fromkeys(
        SUMMONING_SEALS,
        Use(CHEST_AIMS, 10.0, False, 'Opening {}', '{}: open', '{} is not here', brings=SEAL_BRINGS),
    ),
    # A closed door across an open passage's walk (objects.txt IsDoor, levels/doors.py): clicked open as a chest is.
    # The Outer Cloister's gate into the Barracks stood shut and the walk did not move, 45 s a game (04:00:40 on
    # 2026-10-20, class 24 at (15141, 4802))
    **dict.fromkeys(door_sizes(), Use(CHEST_AIMS, 10.0, False, 'Opening the door to {}', '{}: the door is open',
                                      'no door to {} is here')),
}  # fmt: skip
THING_REACH = 25.0  # world units from the character to an object it is sent to by a click
THING_SECONDS = 4.0  # the walk to it and what follows
LOOKS = 2  # times the aims are looked at for a door under them before one is clicked without (0.14 s an aim)


class Entries:
    """Remembered entry spots: `offset` gives a door's, `learn` keeps one; a JSON file when `path` is set."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.known: dict[str, tuple[float, float]] | None = None

    @staticmethod
    def level_key(target: Target) -> str:
        """The door's kind in its level: what a preset not met yet falls back on. The Catacombs' stairs
        presets 291, 292 and 294 are the same block of walls with the same spot beside it."""
        return f'area {target.area}:{target.kind}'

    @staticmethod
    def key(target: Target) -> str:
        """The door's kind in its room's preset: a stairs preset comes in four orientations (N, S, E, W)
        and the spot beside it turns with them, whatever the level; the area stands in without a room."""
        room = room_at(target.rooms, target.point)
        return f'preset {room.preset}:{target.kind}' if room is not None else Entries.level_key(target)

    @staticmethod
    def door_key(target: Target) -> str:
        """The door itself: its preset's key and its label, for two doors of one preset (`KNOWN_ENTRIES`)."""
        return f'{Entries.key(target)}:{target.label}'

    def load(self) -> dict[str, tuple[float, float]]:
        if self.known is None:
            self.known = {}
            if self.path is not None and self.path.exists():
                try:
                    found = json.loads(self.path.read_text())
                    self.known = {key: (float(x), float(y)) for key, (x, y) in found.items()}
                except (OSError, ValueError, TypeError) as exc:
                    LOG.info('Macro: the door entries could not be read (%s)', exc)
        return self.known

    def offset(
        self, target: Target, seeds: Mapping[str, tuple[float, float]] | None = None
    ) -> tuple[float, float] | None:
        """The door's: its own learnt row, its row of `seeds`, its preset's learnt row, its level's."""
        known, door = self.load(), self.door_key(target)
        return (
            known.get(door)
            or (seeds or {}).get(door)
            or known.get(self.key(target))
            or known.get(self.level_key(target))
        )

    def learn(self, target: Target, offset: tuple[float, float]) -> None:
        known = self.load()
        spot = (round(offset[0], 1), round(offset[1], 1))
        known[self.door_key(target)] = known[self.key(target)] = known[self.level_key(target)] = spot
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(known, indent=1, sort_keys=True))
            except OSError as exc:
                LOG.info('Macro: the door entries could not be written (%s)', exc)


ENTRIES = Entries(DEFAULT_ENTRIES)
AIMS = Entries(DEFAULT_AIMS)  # the aim that took each door last, kept the same way


def entry_offset(target: Target) -> tuple[float, float] | None:
    """The entry spot of `target`'s door from its mark (world units): learnt, else seeded (`DOOR_SEEDS`)."""
    return ENTRIES.offset(target, KNOWN_ENTRIES if DOOR_SEEDS else None)


def entry_spot(target: Target) -> Point | None:
    """The remembered spot beside `target`'s door (tiles), if any."""
    offset = entry_offset(target) if target.warp else None
    if offset is None:
        return None
    door = scaled(target.point)
    return (door[0] + offset[0]) / TILE_UNITS, (door[1] + offset[1]) / TILE_UNITS


def entry_stand(target: Target) -> Point | None:
    """Where the character stands to click `target`'s door (tiles): its remembered spot (`entry_spot`) where a hop
    lands as aimed (`footing`, or no grid read there), else the sub-tile centre with footing nearest it within
    STAND_SNAP over open ground from it (of two as near, the nearer the mark); the remembered spot where none has, or
    where the grids have it off the walkable ground (a spot the character stood on is on it). A level run's last hop
    lands on it (macros/goals.py `way_out`) and the door's step clicks from it (`step_toward`)."""
    entry = entry_spot(target)
    if entry is None or not target.ground:
        return entry
    ground = Ground(target.ground)
    at, door = scaled(entry), scaled(target.point)
    if footing(ground, entry) is not False or not ground.walkable(*at):
        return entry
    reach = math.ceil(STAND_SNAP)
    found: list[tuple[float, float, Point]] = []
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            spot = (math.floor(at[0]) + 0.5 + dx, math.floor(at[1]) + 0.5 + dy)
            away = math.dist(spot, at)
            if away > STAND_SNAP or footing(ground, (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS)) is not True:
                continue
            if not clear_walk(ground, at, spot, STAND_SNAP):
                continue  # beyond a wall from the spot
            found.append((round(away, 1), math.dist(spot, door), spot))
    if not found:
        return entry
    spot = min(found)[2]
    return spot[0] / TILE_UNITS, spot[1] / TILE_UNITS


VIEW_STEP = 0.03  # of the window, between the landing spots tried across the view
MIN_GAIN = 3.0  # world units a hop must take off the way to go, or it is not made
# Pixels the pointer may differ from where the macro put it: any. The player's hand works the mouse
# while tapping the key, and a swipe never stops a step (400 still stopped two in the Catacombs); the
# aim is checked and made again instead (`Actuator.aim`).
POINTER_DRIFT = 10**6
HOST_VIEW = Viewport()  # the window a potential is planned for when none is given (16:9, the host's)
REACH_TILES = 5  # tiles one hop of the near potential may span, from anywhere on a tile (`hop_in_view`)
# The far potential, the one a hop is planned by: hops of up to FAR_TILES, counted from tile centre to
# tile centre where the window lets a teleport be aimed (`Viewport.hop_between`), so a band of no
# footing five tiles wide is crossed where the window shows the other side. Up and left the window
# shows 31 units, down and right 26 (34 beside the skill bar), so a cliff may be crossed one way and
# not the other. It counts hops the character cannot make from where on its tile it stands; when it
# finds no landing, the near potential (every hop of which can be made) takes the target over for
# FAR_DISTRUST seconds: for the target and not for the place, since the two potentials do not agree
# on which way is nearer and a hop by each in turn could go back and forth.
FAR_TILES = 6
FAR_DISTRUST = 30.0
FAR_FAILED: dict[tuple[int, int, int], float] = {}  # (area, the target's tile) -> clock time the far way failed


def in_view(point: tuple[float, float]) -> bool:
    return Viewport().in_view(point)


def ground_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where the ground at world (x, y) is drawn (view.py): no lift onto a body."""
    return Viewport(aspect).ground((player.x, player.y), x, y)


def footing(ground: Ground, point: Point) -> bool | None:
    """Whether a teleport aimed at `point` (tiles) finds ground: the sub-tile and its neighbours a
    world unit around are walkable by the read grids. None where no grid covers the spot."""
    x, y = scaled(point)
    centre = ground.walkable(x, y)
    if centre is None:
        return None
    around = (ground.walkable(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return centre and all(known is not False for known in around)


def hop_in_view(dx: int, dy: int, view: Viewport = HOST_VIEW) -> bool:
    """Whether a hop of (dx, dy) tiles lands in view from anywhere on the tile it starts from. The view
    is not round: it shows 23 world units up the screen and 18 down to the skill bar, so a gap that is
    crossed going up may not be crossed coming down. The potential counted five tiles every way, and a
    seek step stood still for good where the only way on was 21 units straight down the screen (host,
    19:19 on 2026-10-10, Catacombs 1). The window's own shape decides (`view`): a narrower window
    shows less to the sides (review.md, finding 8)."""
    return view.hop_in_view(dx, dy)


class Way:
    """The way to go from any spot, in tiles: a potential over the landable tiles of the level,
    Dijkstra from the mark's tile with hops of at most REACH_TILES between landable tiles, walls in
    between or not (a teleport crosses them). A tile is landable when its centre has footing by the
    read grids, or lies on a room no grid covers; the mark's tile always is. A hop is one the window
    shows (`view`, the same value the landing is chosen under), so every hop planned can be made."""

    def __init__(self, target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> None:
        # Kept for the landing: built once here, where it was built anew for each of the 800-odd spots a
        # landing looks at (47-150 ms of every hop, and the recorder's late frames before a hop).
        ground = self.ground = Ground(target.ground)
        self.view = view
        self.rooms = target.rooms
        landable: set[tuple[int, int]] = set()
        for room in self.rooms:
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    known = footing(ground, (x + 0.5, y + 0.5))
                    if known or known is None:
                        landable.add((x, y))
        self.mark = target.point
        mark = (math.floor(target.point[0]), math.floor(target.point[1]))
        landable.add(mark)
        # (dx, dy) leads from a tile to one a hop may come from: the hop itself is (-dx, -dy).
        self.reach = reach = FAR_TILES if far else REACH_TILES
        self.sees = sees = view.hop_between if far else view.hop_in_view
        offsets = [
            (dx, dy, math.hypot(dx, dy))
            for dx in range(-reach, reach + 1)
            for dy in range(-reach, reach + 1)
            if 0 < math.hypot(dx, dy) <= reach and sees(-dx, -dy)
        ]
        self.cost = {mark: 0.0}
        queue = [(0.0, mark)]
        while queue:
            here_cost, (x, y) = heapq.heappop(queue)
            if here_cost > self.cost[x, y]:
                continue
            for dx, dy, step in offsets:
                there = (x + dx, y + dy)
                if there in landable and here_cost + step < self.cost.get(there, math.inf):
                    self.cost[there] = here_cost + step
                    heapq.heappush(queue, (here_cost + step, there))

    def on_rooms(self, point: Point) -> bool:
        return room_at(self.rooms, point) is not None

    def to_go(self, point: Point) -> float:
        """Tiles left from `point`: its tile's potential plus the way to the tile's centre, or to the
        mark itself in the mark's tile, so the mark is the one spot with nothing left."""
        tile = (math.floor(point[0]), math.floor(point[1]))
        cost = self.cost.get(tile)
        if cost is None:
            return math.inf
        anchor = self.mark if cost == 0.0 else (tile[0] + 0.5, tile[1] + 0.5)  # ruff: ignore[float-equality-comparison] the mark's own 0
        return cost + math.dist(point, anchor)

    def from_here(self, point: Point) -> float:
        """Tiles left from where the character stands: as `to_go`, or, when its own tile is not landable
        (a lava edge in the River of Flame), the best landable tile one hop away."""
        here = self.to_go(point)
        if here < math.inf:
            return here
        tx, ty = math.floor(point[0]), math.floor(point[1])
        return min(
            (
                self.to_go(centre) + math.dist(point, centre)
                for dx in range(-self.reach, self.reach + 1)
                for dy in range(-self.reach, self.reach + 1)
                if (tx + dx, ty + dy) in self.cost and self.sees(dx, dy)
                for centre in [(tx + dx + 0.5, ty + dy + 0.5)]
                if math.dist(point, centre) <= self.reach
            ),
            default=math.inf,
        )


@lru_cache(maxsize=8)
def way_for(target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> Way:
    """The potential of a target under a window's shape, kept across presses: rooms, grids, mark and
    window rarely change within a level."""
    return Way(target, view, far)


def spots_in_view(player: Player, aspect: float):
    """Ground points drawn across the view, in tiles, VIEW_STEP of the window apart."""
    (left, right), (top, _) = VIEW
    view = Viewport(aspect)
    columns, rows = int((right - left) / VIEW_STEP) + 1, int((CORNER_BOTTOM - top) / VIEW_STEP) + 1
    for column in range(columns):
        for row in range(rows):
            across, down = left + column * VIEW_STEP, top + row * VIEW_STEP
            if view.hop_view((across, down)):  # the rows beside the skill bar too, while the corners are on
                x, y = world_point(player, across, down, aspect)
                yield x / TILE_UNITS, y / TILE_UNITS


def landable(target: Target, way: Way, point: Point) -> bool:
    """Whether a hop may be aimed at `point` (tiles): footing by the read grids, else a room's rectangle."""
    known = footing(way.ground, point)
    return known if known is not None else way.on_rooms(point)


def entry_in_view(target: Target, player: Player, way: Way, aspect: float) -> Point | None:
    """Where the character stands to click the door (tiles, `entry_stand`) when a hop from here can land on it."""
    entry = entry_stand(target)
    if entry is None or not in_view(ground_fraction(player, *scaled(entry), aspect)):
        return None
    return entry if landable(target, way, entry) else None


def landing(
    target: Target, player: Player, way: Way, aspect: float, ring: tuple[float, float] | None = None
) -> tuple[Point, float] | None:
    """The footing in view that leaves the shortest way to the mark, with the tiles it takes off the
    way from where the character stands; None when nothing in view brings it MIN_GAIN nearer. `ring`
    (world units, least and most): only spots that far from the character, for a hop of one length
    (controller mode, macros/pad.py)."""
    start = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    now = way.from_here(start)

    def outside(point: Point) -> bool:
        return ring is not None and not ring[0] <= math.dist(point, start) * TILE_UNITS <= ring[1]

    entry = entry_in_view(target, player, way, aspect)
    if entry is not None and not outside(entry):
        return entry, now - way.to_go(entry)  # the door's own spot is in view: the hop that ends the way
    candidates = (*spots_in_view(player, aspect), *(approaches(target) if target.warp else (target.point,)))
    found: list[tuple[float, float, Point]] = []  # (way to go, distance from the character, spot)
    for point in candidates:
        if outside(point):
            continue
        if target.warp and math.dist(scaled(point), scaled(target.point)) < WARP_TILES:
            continue  # the warp's own tiles: a hop onto them lands anywhere beside
        if not way.view.hop_view(ground_fraction(player, *scaled(point), aspect)) or not landable(target, way, point):
            continue
        found.append((way.to_go(point), math.dist(point, start), point))
    # Only spots that take MIN_GAIN off the way: a spot beside the door with footing on a tile the way
    # does not count (its centre in the wall the stairs sit in) was the nearest "beside" spot, came out
    # as no gain, and sixteen teleport steps in a row stopped 16 units from the door (host, 19:29 on
    # 2026-10-10, Catacombs 1).
    found = [entry for entry in found if now - entry[0] >= MIN_GAIN / TILE_UNITS]
    if not found:
        return None
    beside = [entry for entry in found if math.dist(scaled(entry[2]), scaled(target.point)) <= APPROACH + 1.0]
    if target.warp and beside:  # a spot beside the door: the one nearest the character, on its side
        cost, _, spot = min(beside, key=lambda entry: entry[1])
    else:
        cost, _, spot = min(found)
    return spot, now - cost


def approaches(target: Target) -> list[Point]:
    """Spots (tiles) APPROACH units around a warp, where the last hop may land."""
    cx, cy = scaled(target.point)
    return [
        ((cx + APPROACH * math.cos(angle)) / TILE_UNITS, (cy + APPROACH * math.sin(angle)) / TILE_UNITS)
        for angle in (2 * math.pi * k / BEARINGS for k in range(BEARINGS))
    ]


def scaled(tile: Point) -> Point:
    return tile[0] * TILE_UNITS, tile[1] * TILE_UNITS


def moved(player: Player, since: Player) -> bool:
    return player.area != since.area or math.dist((player.x, player.y), (since.x, since.y)) >= MOVED


def missed_from(area: int, here: Point, spot: Point) -> float | None:
    """How far the last hop landed off its aim (MISSED) when `spot` is that aim again and the character stands where
    it landed, in the same level: a hop from there lands no nearer (hunting/moves.py REHOP_WALK). None otherwise."""
    if not MISSED:
        return None
    aim, landed, level = MISSED[0]
    if level != area or math.dist(aim, spot) > REHOP_SAME or math.dist(landed, here) >= MOVED:
        return None
    return math.dist(aim, landed)


def landed_from(player: Player, since: Player, aim: Point) -> bool:
    """Whether a hop aimed at `aim` (world units) has taken the character there: it has moved, and it
    stands or is near the aim. A character walking when the hop began moves before the hop does: the
    walk was taken for the landing ("landed …, off by 24" 0.2 s after the key, 2026-10-10 and after)."""
    if not moved(player, since):
        return False
    return player.area != since.area or player.mode not in WALKING or math.dist((player.x, player.y), aim) < MOVED


def take_teleport(run: Run, key_names) -> None:
    """Have the Teleport key in `run.keys` and the staff that casts it in hand, if a staff it is."""
    world = run.world()
    if TELEPORT not in world.slots:
        raise Abort('Teleport is not on a skill key')
    staff = run.reads.teleport()
    if staff is None:
        run.keys = key_names(world, (TELEPORT,))
        return
    if staff.charges == 0:
        raise Abort('the Teleport staff has no charges left')
    if staff.in_hand:
        run.keys = key_names(world, (TELEPORT,))
        return
    run.keys = key_names(world, (TELEPORT, SWAP_WEAPONS))

    def in_hand() -> bool:
        now = run.reads.teleport()
        return now is not None and now.in_hand

    if not swap_until(run, in_hand):  # pressed again when the game drops it (routines.swap_until)
        raise Abort('the Teleport staff is not in hand after the swaps')
    run.pause('key')


def box_aim(door: Point, warps: tuple[Warp, ...]) -> tuple[int, int] | None:
    """The middle of the click box of the door unit nearest `door` (the mark, world units), in classic
    pixels from the mark; None when no door unit is within WARP_NEAR of it or its box is not known.
    The tower's door in Black Marsh (host, 2026-10-10): the unit 6.5, 2.5 units from the mark, the box
    42 to 122 pixels above it, the aims 45 above on its edge (5 of 9 took)."""
    near = [warp for warp in warps if math.dist((warp.x, warp.y), door) <= WARP_NEAR]
    if not near:
        return None
    warp = min(near, key=lambda found: math.dist((found.x, found.y), door))
    box = warp_box(warp.warp)
    if box is None:
        return None
    dx, dy = warp.x - door[0], warp.y - door[1]
    return round((dx - dy) * 16 + (box[0] + box[2]) / 2), round((dx + dy) * 8 + (box[1] + box[3]) / 2)


def door_aims(target: Target, warps: tuple[Warp, ...] = ()) -> tuple[tuple[int, int], ...]:
    """The aims to try in turn: the middle of the door's own click box when the game shows the door
    (`box_aim`), then the one that took this door before (learnt, `AIMS`, else from KNOWN_AIMS), then
    the rest of DOOR_AIMS."""
    learnt = AIMS.offset(target)
    took = (round(learnt[0]), round(learnt[1])) if learnt is not None else KNOWN_AIMS.get(Entries.key(target))
    first = [aim for aim in (box_aim(scaled(target.point), warps), took) if aim is not None]
    return tuple(dict.fromkeys((*first, *DOOR_AIMS)))


def walk_into(run: Run, target: Target, player: Player, aspect: float) -> None:
    """Click the door and watch the walk: where the mark is, where the character started, how long and
    how far it walked and where it stood when the level changed (the last hop's landing is judged by
    the walk it leaves). The door's entry is where the character stood at the click when the first
    click took (a spot the door is proven to take a click from: the cellar stairs took it from 5.6
    units without a step), else where it stood when the level changed. With the game's record of the
    unit under the pointer (`run.hovered`) an aim is clicked only with a door under it; the aims that
    show none are looked at once more, then clicked as they are. An aim with another unit under
    the pointer waits for the others; after them all the first is made once more, from where the
    clicks on the ground left the character (the tower's door in Black Marsh, host, 20:12 on
    2026-10-10: nothing took from the remembered spot, the same aim took on the next press)."""
    door = scaled(target.point)
    if run.pad is not None:
        pad_door(run, target, player)  # controller mode: the door unit targeted and A (macros/pad.py)
        return
    if not in_view(ground_fraction(player, *door, aspect)):
        raise Abort(f'{target.label} is not in view')
    start = (player.x, player.y)
    known = entry_offset(target)
    warps = run.warps() if run.warps is not None else None
    warp_at = nearest_warp(warps, door, WARP_NEAR)  # the door's warp unit, from the mark: its entry is learnt by it too
    objects = object_door(warps, door, WARP_NEAR)  # no warp tile: the entrance is an object (targeting.OBJECT_DOORS)
    run.say(f'Walking into {target.label}, {math.dist(start, door):.0f} away')
    LOG.info(
        'Macro: door %s marked at (%.1f, %.1f); the character at (%.1f, %.1f), %.1f from the mark; entry %s',
        target.label, *door, *start, math.dist(start, door),
        'not known yet' if known is None else f'remembered {known[0]:+.1f}, {known[1]:+.1f} from the mark',
    )  # fmt: skip
    began = run.clock()
    last, walked, clicks = start, 0.0, 0

    def aim_at(aim: tuple[int, int]) -> bool:
        across, down = ground_fraction(player, *door, aspect)
        where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
        if not in_view(where):
            return False
        run.actuator.aim(*where, scatter=(4, 3))
        return True

    def under() -> tuple[int, int] | None:
        if run.hovered is None:
            return None
        run.pace.sleep(HOVER_SECONDS)
        return run.hovered()

    def click(aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
        """A click where the pointer is, with the character free of its last cast, made again when it
        moved nobody; whether the level changed."""
        for again in range(DOOR_CLICKS):
            settle(run, 0.0, STILL_SECONDS)
            stood = (player.x, player.y)
            if press(aim, over):
                return True
            if math.dist((player.x, player.y), stood) >= MOVED:
                break  # a click on the ground: the door is not under this aim
            if again + 1 < DOOR_CLICKS:
                LOG.info('Macro: the click %s pixels from the door moved nobody; made again', aim)
        return False

    def press(aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
        """One click where the pointer is; whether the level changed."""
        nonlocal player, last, walked, clicks
        clicks += 1
        stood = (player.x, player.y)
        run.actuator.click()
        deadline, still, stirred = run.clock() + DOOR_SECONDS, run.clock() + STILL_SECONDS, False
        while True:
            world = run.world()
            now = world.player
            if now is None or now.area != target.area:
                AIMS.learn(target, aim)
                offset = (last[0] - door[0], last[1] - door[1])
                from_mark = (stood[0] - door[0], stood[1] - door[1])
                if clicks == 1 and walked < NO_WALK and entry_learnable(from_mark, warp_at, ENTRY_MAX):
                    offset = from_mark  # proven: one click from here is the step in
                learns = entry_learnable(offset, warp_at, ENTRY_MAX)  # by the warp unit too (targeting.ENTRY_FROM_WARP)
                if learns and walked >= NO_WALK and known is not None:
                    # A walk in: where the level changed replaces the remembered spot only when it was the spot
                    # clicked from (it needed the walk); a walk from elsewhere says nothing against it
                    learns = math.dist(stood, (door[0] + known[0], door[1] + known[1])) <= ENTRY_NEAR
                LOG.info('Macro: the door took the click %s pixels from its tiles; under the pointer %s', aim, over)
                LOG.info(
                    'Macro: door %s: in after %.2fs, walked %.1f from (%.1f, %.1f) to (%.1f, %.1f); the entry '
                    'at %+.1f, %+.1f from the mark, %.1f away (%s)',
                    target.label, run.clock() - began, walked, *start, *last, *offset, math.hypot(*offset),
                    'remembered' if learns
                    else 'not remembered: too far from the mark' if not entry_learnable(offset, warp_at, ENTRY_MAX)
                    else 'not remembered: walked in from elsewhere',
                )  # fmt: skip
                if learns:
                    ENTRIES.learn(target, offset)
                run.say(f'{target.label}: there')
                return True
            here = (now.x, now.y)
            walked += math.dist(here, last)
            last = here
            stirred = stirred or here != stood
            if run.clock() >= deadline or (run.clock() >= still and not stirred):
                break  # no way in, or nobody moved: the click was swallowed
            run.pace.sleep(WALK_POLL)
        player = run.world().player or player  # the click on the ground walked the character
        LOG.info(
            'Macro: the door did not take the click %s pixels from its tiles; under the pointer %s; the character '
            'now at (%.1f, %.1f)',
            aim, over, player.x, player.y,
        )  # fmt: skip
        return False

    aims = door_aims(target, warps or ())
    waiting, unseen, empty = [], list(aims), []
    for _ in range(LOOKS):
        looked, unseen = unseen, []
        for aim in looked:
            if not aim_at(aim):
                continue
            over = under()
            does = door_hover(over, nothing=over is None and nothing_under(run), objects=objects)
            if does == CLICK:
                if click(aim, over):
                    return
            elif does == WAIT:
                LOG.info('Macro: the aim %s pixels from the door has the unit %s under it; left for last', aim, over)
                waiting.append(aim)
            elif does == EMPTY:
                if aim not in empty:
                    LOG.info('Macro: the aim %s pixels from the door has nothing under it; left till the others', aim)
                    empty.append(aim)
            else:
                unseen.append(aim)
        if not unseen:
            break
    if unseen:
        LOG.info('Macro: no door under the pointer at the aims %s after %d looks; clicking them', unseen, LOOKS)
    for aim in (*unseen, *empty, *waiting, *aims[:1]):
        if aim_at(aim) and click(aim, under()):
            return
    raise Abort(f'no click took {target.label}', cause='door')


def pad_door(run: Run, target: Target, player: Player) -> None:
    """Controller mode: into the door of `target` by the pad (macros/pad.py): its door unit targeted and A
    pressed from beside it (the client's Interact group takes doors, inferred), else a walk from the door's entry
    spot through its mark and on (as the keyboard's click on the door's tiles walks), then A on a door tile the
    client's own target names; the level changing is the evidence."""
    assert run.pad is not None
    door = scaled(target.point)
    run.say(f'Walking into {target.label}, {math.dist((player.x, player.y), door):.0f} away')

    def inside(world: World | None = None) -> bool:
        now = (world or run.world()).player
        return now is None or now.area != target.area

    doors = run.warps() if run.warps is not None else ()
    near = [warp for warp in doors if math.dist((warp.x, warp.y), door) <= WARP_NEAR]
    if near:
        unit = min(near, key=lambda warp: math.dist((warp.x, warp.y), door))
        if run.pad.interact(TILE_UNIT, unit.unit_id, (unit.x, unit.y), inside, target.label):
            run.say(f'{target.label}: there')
            return
    # No door unit to target: through the door as the keyboard's click on its tiles goes (the Chaos Sanctuary's on
    # 2026-10-14, 22:09:24: the click walked the character 2.7 units from its entry spot to 2.4 from the mark, and it
    # was in). The stick is held from the entry spot (where one comes out of the door) through the mark and on past
    # it, not onto the entry spot outside it (22:09:08: "did not take the pad", run-1904-findings.md §3.5).
    entry = entry_spot(target)
    here = (player.x, player.y)
    start = scaled(entry) if entry is not None else here
    if entry is not None and math.dist(here, start) > DOOR_LINE:
        run.pad.walk(start, done=inside, why=target.label)  # onto the door's line first
        if inside():
            run.say(f'{target.label}: there')
            return
    line = (door[0] - start[0], door[1] - start[1])
    length = math.hypot(*line)
    past = door if length < 1e-6 else (door[0] + line[0] / length * DOOR_PAST, door[1] + line[1] / length * DOOR_PAST)
    run.pad.walk(past, near=0.5, done=inside, why=target.label)
    if inside():
        LOG.info('Macro: door %s by the pad: walked in through the mark from %s', target.label, _spot(start))
        run.say(f'{target.label}: there')
        return
    # Stood at the door: the client's own target names a door tile now (its Interact group reaches 5.2 units): A
    held = run.pad.target()
    now = run.world().player
    if held is not None and held[0] == TILE_UNIT and now is not None:
        LOG.info(
            'Macro: door %s by the pad: the walk did not take it; the client targets tile %d: A', target.label, held[1]
        )
        if run.pad.interact(TILE_UNIT, held[1], (now.x, now.y), inside, target.label):
            run.say(f'{target.label}: there')
            return
    raise Abort(
        f'{target.label} did not take the pad (walked through the mark from {_spot(start)}, no door tile targeted)',
        cause='door',
    )


def _spot(point: Point) -> str:
    return f'({point[0]:.1f}, {point[1]:.1f})'


def marked_thing(run: Run, target: Target) -> Thing | None:
    """The object the mark names: the one of its kind nearest the mark among those the game shows near it."""
    mark, use, kinds = scaled(target.point), USES[target.use], classes(target.use)
    near = [
        t
        for t in (run.things() if run.things is not None else ())
        if t.txt_id in kinds and math.dist((t.x, t.y), mark) <= use.near
    ]
    return min(near, key=lambda t: math.dist((t.x, t.y), mark)) if near else None


def used_already(use: Use, thing: Thing) -> bool:
    """Whether the object was used before: its mode left 0 on one that neither leaves nor opens a panel (a chest, a
    seal, a body). The mark is only a place then, and nothing more comes of it (no `Use.brings` wait)."""
    return not use.leaves and not use.opens and bool(thing.mode)


def use_thing(run: Run, target: Target, player: Player, thing: Thing, aspect: float) -> None:
    """Click the object's picture and watch the walk until it took: the level changed (a portal), its panel opened
    (the stash, a waypoint) or the object's mode did (a body searched). An aim is clicked only with the object under
    the pointer by the game's own record (`run.hovered`); without that record the aims are clicked as they are. An
    object with a panel or one that leaves is looked at before the first aim (PANEL_GRACE with a panel, else one
    look), before each aim after it and after the last: once it took, no aim more."""
    use, at = USES[target.use], (thing.x, thing.y)
    if used_already(use, thing):
        run.say(f'At {target.label}')  # used already: the mark is only a place now
        return
    run.say(f'{use.begun.format(target.label)}, {math.dist((player.x, player.y), at):.0f} away')
    LOG.info(
        'Macro: object %d (class %d, mode %d, selectable %s) of %s at (%.1f, %.1f), %.1f from the mark; the character '
        'at (%.1f, %.1f)',
        thing.unit_id, thing.txt_id, thing.mode, thing.selectable, target.label, *at,
        math.dist(at, scaled(target.point)), player.x, player.y,
    )  # fmt: skip

    def took_in(world: World) -> bool:
        if use.opens:
            return use.opens in world.open_panels
        now = world.player
        if use.leaves:
            return now is None or now.area != target.area
        return any(t.unit_id == thing.unit_id and t.mode for t in (run.things() if run.things is not None else ()))

    def took() -> bool:
        return took_in(run.world())

    def taken(when: str, seconds: float = 0.0) -> bool:
        """Whether it took before the aim about to be made (a click before it brought it): said, and no aim. Asked of a
        panel or a level change only: a chest's mode is not looked at between the aims (its look costs every chest of
        the loop a read an aim, and no click but the aims' opens one: `thing.mode` above sees one used before)."""
        if not (use.opens or use.leaves) or until(run, took_in, seconds, poll=WALK_POLL) is None:
            return False
        LOG.info('Macro: %s took %s: not clicked again', target.label, when)
        run.say(use.done.format(target.label))
        return True

    if run.pad is not None:  # controller mode: stand by it, the target names it, A (macros/pad.py)
        if run.pad.interact(OBJECT_UNIT, thing.unit_id, at, took, target.label):
            run.say(use.done.format(target.label))
            return
        raise Abort(f'{target.label} did not take the pad')
    # The effect looked for before the first aim and between the aims: the walk's last click lands on the object
    # itself (shop.py `walk_until`), and the panel it opens 0.05-0.19 s after the stop covers the object, so every aim
    # read nothing under the pointer: "not under the pointer at any aim" with the panel open, the waypoint's step back
    # clicked onto it (14:42:09 on 2026-10-18; seven such incidents in five modules, rca/2026-10-18/arch-actions.md
    # §2 A)
    if taken('before any aim', PANEL_GRACE if use.opens else 0.0):
        return
    if THRONE_WAITS and target.use == THRONE_PORTAL:
        baal_gone(run, target.label)
        player = run.world().player or player
    seen = False
    covered: set[int] = set()  # the monsters under the pointer at an aim that was not clicked
    try:
        for n, aim in enumerate(use.aims):
            if n and taken(f'before aim {aim}'):
                return
            across, down = ground_fraction(player, *at, aspect)
            where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
            if not in_view(where):
                continue
            run.actuator.aim(*where, scatter=(4, 3))
            if run.hovered is not None:
                run.pace.sleep(HOVER_SECONDS)
                over = run.hovered()
                if over != (OBJECT_UNIT, thing.unit_id):
                    LOG.info('Macro: the aim %s pixels from %s has %s under it; not clicked', aim, target.label, over)
                    if over is not None and over[0] == MONSTER_UNIT:
                        covered.add(over[1])
                    continue
            seen = True
            for _ in range(DOOR_CLICKS):
                settle(run, 0.0, STILL_SECONDS)
                stood = (player.x, player.y)
                run.actuator.click()
                deadline, still, stirred = run.clock() + THING_SECONDS, run.clock() + STILL_SECONDS, False
                while True:
                    if took():
                        LOG.info('Macro: %s took the click %s pixels from its ground', target.label, aim)
                        run.say(use.done.format(target.label))
                        return
                    player = run.world().player or player
                    stirred = stirred or (player.x, player.y) != stood
                    if run.clock() >= deadline or (run.clock() >= still and not stirred):
                        break
                    run.pace.sleep(WALK_POLL)
                LOG.info(
                    'Macro: %s did not take the click %s pixels from its ground; the character now at (%.1f, %.1f)',
                    target.label, aim, player.x, player.y,
                )  # fmt: skip
                if stirred:
                    break  # it walked and nothing came of it: the next aim, from where it stands
    except Abort as stop:
        if covered and not isinstance(stop, Covered) and EXPIRED in str(stop):
            # The act's priced time ran out with a monster seen on the object (21:16:22 on 2026-10-17: two aims at a
            # chest had a monster under them, then four tries in 6.5 s until it walked off): told as in the way, so
            # the fight with it comes first (hunting/judging.py `blocked`), not the same click again
            raise Covered(f'{target.label}: {stop}', covered) from stop
        raise
    if taken('after the last aim'):
        return
    if not seen:
        if covered:
            raise Covered(f'{target.label} is not under the pointer at any aim', covered)
        raise Untook(f'{target.label} is not under the pointer at any aim')
    raise Untook(f'no click took {target.label}')


# 2026-10-21 17:24:25.9-17:24:38.6: the Throne's portal clicked 16 times while Baal (543, then 559) was read, the last
# 0.1 s after he was gone, and none took (the game opens the Chamber only as 559 reaches it: hunting/throne.py
# `portal_shut`). True: with Baal read, no click until he is gone (BAAL_WAIT at most), then PORTAL_OPENS; any hostile
# in the hall meanwhile ends the wait (`Untook`: the level run fights it). False: the aims at once, as before
THRONE_WAITS = True
BAAL_WAIT = 25.0  # seconds: he walked 1.6 s, 10.0-11.3 s after the fifth wave's last hall monster died (5 takes)


def baal_gone(run: Run, label: str) -> None:
    """Wait for Baal to leave his throne before the portal is clicked (THRONE_WAITS); nothing when he is not read."""
    from inventory_tracking.macros.hunting import throne  # here: hunting imports this module

    def hall(world: World) -> bool:
        seat = throne.seat_of(world.monsters)
        return seat is not None and any(
            m.owner == NO_OWNER and not m.ally and m.txt_id not in throne.BAAL and m.mode not in (0, 12)
            and math.dist(seat, (m.x, m.y)) <= throne.HALL_UNITS
            for m in world.monsters
        )  # fmt: skip

    world = run.world()
    if throne.seat_of(world.monsters) is None:
        return
    LOG.info('Macro: %s: Baal is still on his throne: no click until he is gone (at most %.0f s)', label, BAAL_WAIT)
    run.say(f'{label}: waiting for Baal to leave his throne')
    seen = until(run, lambda w: throne.seat_of(w.monsters) is None or hall(w), BAAL_WAIT, poll=WALK_POLL)
    if seen is None:
        raise Untook(f'{label}: Baal did not leave his throne in {BAAL_WAIT:.0f} s')
    if hall(seen):
        raise Untook(f'{label}: the throne hall is not clear: fought first')
    LOG.info('Macro: %s: Baal is gone into the portal: %.1f s more before the click', label, throne.PORTAL_OPENS)
    run.pace.sleep(throne.PORTAL_OPENS)


def world_slots(world) -> str:
    return ','.join('-' if skill is None else str(skill) for skill in world.slots)


def ready(run: Run) -> tuple[Player, tuple[int, int, int, int]]:
    """The checks every step shares: in a game, nothing open, a game window. (the player, the window rect)."""
    world, rect = ready_world(run)
    assert world.player is not None
    return world.player, rect


def _tidied(run: Run, world: World) -> bool:
    from inventory_tracking.macros.cube import tidy  # cube.py imports the step's helpers

    return bool(tidy(run, world))


def ready_world(run: Run) -> tuple[World, tuple[int, int, int, int]]:
    """`ready` with the world it read (one read: its doors, its monsters), the player in it."""
    world = run.world()
    if world.player is None:
        raise Abort('not in a game')
    if world.open_panels and _tidied(run, world):
        world = run.world()  # the loop's own panels left open by a cancelled routine: closed (cube.py `tidy`)
    if world.open_panels:
        raise Abort(f'{world.open_panels[0]} is open')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    run.actuator.drift = POINTER_DRIFT
    return world, rect


def _around(target: Target, here: Point, spot: Point) -> bool:
    """Whether the walked way from `here` to the door's remembered `spot` is ENTRY_AROUND or shorter."""
    from inventory_tracking.macros.travel import walked_length  # late: travel imports this module

    return walked_length(Ground(target.ground), (), here, spot) <= ENTRY_AROUND


def clear_walk(ground: Ground, start: Point, end: Point, reach: float) -> bool:
    """Whether `end` is within `reach` of `start` over ground known to be walkable all the way (world units)."""
    away = math.dist(start, end)
    if away > reach:
        return False
    steps = max(1, math.ceil(away * 2))
    return all(
        ground.walkable(start[0] + (end[0] - start[0]) * k / steps, start[1] + (end[1] - start[1]) * k / steps)
        for k in range(steps + 1)
    )


CARD_POLL = 0.05
CARD_SECONDS = 1.2  # for the level card to follow the character into a new level (0.84 s the longest logged)


def card_for(run: Run, read: Callable[[], Target | None] | None, seconds: float = CARD_SECONDS) -> Target | None:
    """The level card's mark, waited for while the card is still the level just left: the service
    reads the new level's card 0.37 s after the arrival at the median (57 logged arrivals), and a
    step asked for meanwhile stopped with "the level card is for another level" (15 of 116 exits
    to 2026-10-10, and after both stairs of the first Worldstone Keep run)."""
    if read is None:
        return None
    until, hurried = run.clock() + seconds, False
    while True:
        with run.lightly():
            target, player = read(), run.world().player
        if player is None or (target is not None and target.area == player.area) or run.clock() >= until:
            return target
        if not hurried and run.hurry is not None:
            # The service looks at the level every half second and sleeps up to 0.2 s between its
            # passes: asked to look now (Tower Cellar 1, 21:36:39 on 2026-10-11: the press on arrival
            # took 580 ms to its click, the others in that session 140 to 200).
            hurried = True
            run.hurry()
        run.pace.sleep(CARD_POLL)


def step_toward(
    run: Run,
    target: Target | None,
    key_names,
    afoot: Callable[[Target], None] | None = None,
    warp: Callable[[Target, Player, tuple[float, float]], bool] | None = None,
    *,
    empty: Callable[[Target], bool] | None = None,
) -> None:
    """One teleport step. `key_names(world, skills)` gives the key per skill (runner). `afoot` makes the
    step without Teleport (the runner: the navigator's way for the means in hand, a Blade Warp or a walk) when
    the staff has no charge left; `warp` makes a hop by Blade Warp where it can (`hop_toward`). `empty(target)`: at
    a `use` mark with none of its objects shown, whether the route took the mark as done (route.note_empty); else the
    step stops saying the object is not here."""
    with run.lightly():
        player, rect = ready(run)
    run.in_time('the step')
    if target is None:
        raise Abort('nothing is marked on the level card (Win+C shows it)')
    if target.area != player.area:
        raise Abort('the level card is for another level')
    if target.kind == 'previous':
        # The way back is the first mark only where nothing leads on: the step after the door into
        # Tower Cellar 5 clicked the stairs back up to level 4 (host, 20:06 on 2026-10-10).
        raise Abort(f'the only way marked is back to {target.label}')
    aspect = rect[2] / rect[3]
    here = (player.x, player.y)
    if target.use:
        thing = marked_thing(run, target)
        at_mark = math.dist(here, scaled(target.point)) <= SPOT_NEAR  # no hop leads nearer than this
        if thing is not None and (at_mark or math.dist(here, (thing.x, thing.y)) <= THING_REACH):
            use_thing(run, target, player, thing, aspect)
            return
        if thing is None and at_mark:
            # The game shows the objects a screen round the character: none at the mark is none there.
            if empty is not None and empty(target):
                return
            raise Abort(USES[target.use].absent.format(target.label))
    entry = entry_stand(target)  # the remembered spot, on footing: where a level run's last hop lands
    if entry is not None and math.dist(here, scaled(entry)) <= ENTRY_NEAR:
        at_door = True  # on the door's own spot: clicked from here
    elif entry is not None and clear_walk(Ground(target.ground), here, scaled(entry), ENTRY_WALK):
        at_door = True  # a few steps straight to the spot: the click walks them, and a hop is saved
    elif (
        entry is not None
        and target.warp
        and math.dist(here, scaled(target.point)) <= NEAR_WARP
        and _around(target, here, scaled(entry))
    ):
        at_door = True  # a short walk round to the spot (the Catacombs stairs' block of walls): cheaper than a hop
    elif entry is not None and entry_in_view(target, player, way_for(target, Viewport(aspect)), aspect) is not None:
        at_door = False  # the spot is a hop away: onto it first, however near the door is
    else:
        at_door = target.warp and math.dist(here, scaled(target.point)) <= NEAR_WARP
    staff = run.reads.teleport()
    if at_door:
        walk_into(run, target, player, aspect)
    elif afoot is not None and staff is not None and staff.charges == 0:
        # user, 2026-10-11: "use warp if we have 0 charges"; 2026-10-14: a way without Teleport is planned for the
        # means in hand, the walked way with Blade Warp over a clear line (rca/2026-10-14/navigation-classes.md).
        # Never toward a place a Teleport would land on: the pocket of 22:54:28 on 2026-10-14, 276 units by the
        # walked way from the door (run-1932-findings.md §1.2.2).
        afoot(target)
    else:
        hop_toward(run, target, player, rect, key_names, warp)


def far_banned(key: tuple[int, int, int], now: float) -> bool:
    """Whether the far way to this target failed less than FAR_DISTRUST seconds ago."""
    failed = FAR_FAILED.get(key)
    if failed is not None and now - failed >= FAR_DISTRUST:
        del FAR_FAILED[key]
        return False
    return failed is not None


def ban_far(key: tuple[int, int, int], now: float) -> None:
    for old in [old for old, failed in FAR_FAILED.items() if now - failed >= FAR_DISTRUST]:
        del FAR_FAILED[old]
    FAR_FAILED[key] = now


def moving(build: Build) -> frozenset[int]:
    """The casts that end with the character somewhere else: Teleport, and every skill the build's
    movement sets jump by."""
    sets = build.movement
    return frozenset((TELEPORT, *(source.jump.skill for movement in sets for source in movement.sources)))


def settled(run: Run, player: Player) -> Player:
    """The character where the hop will start from: once the cast before is over and a walk has
    ended (a walk still going after SETTLE_SECONDS is the player's: the hop goes from where it is).
    The hop is planned and its landing judged from this place. Taken while a walk or the hop before
    was still under way, the place was the one before: the walk's end or that hop's landing then
    counted as this hop's landing, and every hop after was aimed from the place before its own
    (Halls of Death's Calling, 12:32:17 on 2026-10-11: twelve of sixteen hops off by 6 to 26 units)."""
    now = run.world().player
    if now is not None and LANDING:
        x, y, at = LANDING[0]
        if 0 <= run.clock() - at <= LANDING_FRESH and math.dist((now.x, now.y), (x, y)) < MOVED:
            return now  # the hop before has landed here: its cast's tail moves the character no more
    if now is not None and now.mode in ACTING and now.right_skill not in moving(run.build):
        # A cast that takes the character nowhere (a strike of attack mode): it stands where the hop
        # will start, and the key can be pressed during the cast (`press_hop`).
        return now
    free = run.seen(lambda w: w.player is not None and w.player.mode not in ACTING, READY_SECONDS, HOP_POLL)
    if free is None:
        return player
    still = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING | ACTING, SETTLE_SECONDS)
    return (still or run.world()).player or player


def press_hop(run: Run, arrived: Callable[[World], bool]) -> None:
    """The Teleport key, pressed at once, also during the cast before: the game keeps a Quick Cast
    key that comes during a cast and casts it on the first frame the character is free, with the
    pointer where it is then (the client's code, read on 2026-10-12: two entries at image offset
    0x1F6ADE4, filled at key-down, the cast issued by the per-frame processor at 0x1400d8650 once
    the mode is none of 7, 8, 10, 18). That is why the key feels instant by hand (user, that day).
    The macro waited to see the cast's end and tapped then: a third of the presses of 22:11 on
    2026-10-11 took 214 to 290 ms to their key for it. The game does not keep every press (one
    under 160 ms after the cast before began with its entry still held, or a third one): when the
    cast before ends and none follows within QUEUED_SECONDS, the key is pressed again."""
    if run.pad is not None:
        # Controller mode: the button once the character is free (the right button's Quick Cast, which the
        # press during a cast below watches for, is the mouse's).
        press_skill(run, TELEPORT, HOP_POLL)
        return
    world = run.world()
    if KEY_DROP_WAIT and world.player is not None and world.player.mode in KEY_DROP_MODES:
        began, mode = run.clock(), world.player.mode
        free = run.seen(lambda w: w.player is None or w.player.mode not in KEY_DROP_MODES, KEY_DROP_SECONDS, HOP_POLL)
        world = free or run.world()
        LOG.info('Macro: Teleport key held %.2fs for the end of mode %d (a block or a hit drops it)',
                 run.clock() - began, mode)  # fmt: skip
    busy = world.player is not None and world.player.mode in ACTING
    press_skill(run, TELEPORT, HOP_POLL, wait=not busy)
    if not busy:
        return
    run.mark('key_in_cast')  # in the press's trace (latency.py): how often, and how often the game kept it
    over = run.seen(
        lambda w: arrived(w) or (w.player is not None and w.player.mode not in ACTING), READY_SECONDS, HOP_POLL
    )
    if over is None or arrived(over):
        return
    taken = run.seen(
        lambda w: arrived(w) or (w.player is not None and w.player.mode in ACTING), QUEUED_SECONDS, HOP_POLL
    )
    if taken is None:
        LOG.info('Macro: the game did not keep the Teleport key pressed during the cast before: pressed again')
        run.mark('key_again')
        press_skill(run, TELEPORT, HOP_POLL)


def hop_toward(
    run: Run,
    target: Target,
    player: Player,
    rect: tuple[int, int, int, int],
    key_names,
    warp: Callable[[Target, Player, tuple[float, float]], bool] | None = None,
) -> None:
    """`_hop_toward`, with the game looked at lightly (`Run.lightly`) but for the `warp` it asks."""
    light = run.light
    try:
        _hop_toward(run, target, player, rect, key_names, warp, light)
    finally:
        run.light = light


def _hop_toward(
    run: Run,
    target: Target,
    player: Player,
    rect: tuple[int, int, int, int],
    key_names,
    warp: Callable[[Target, Player, tuple[float, float]], bool] | None,
    light: int,
) -> None:
    """One teleport toward `target`: the landing in view that leaves the shortest way (the hunt
    keys use it too, macros/hunt.py). `warp(target, player, landing)` is asked first to make the hop
    another way (the teleport step: a Blade Warp over open ground, which costs the staff no charge)
    and says whether it did."""
    run.light = light + 1  # where the character is and what it does: no monsters, no doors
    player = settled(run, player)
    run.mark('settled')
    # Not for a room to explore: its point is the tile of it nearest by the way, and standing a tile
    # short of it is not standing in it (Halls of Vaught, 15:10:20 on 2026-10-11: one tile from the room,
    # "the character is beside it" for 17 presses, the room never seen).
    # Nor for a firing spot at a monster: a few units short of it the shot may still be blocked, and
    # then nothing moved at all (Tower Cellar 5, 20:14:45 on 2026-10-11: the spot 4.1 away round a
    # corner, seven seek steps "beside it", attack mode with none in reach). The place that is
    # arrived at SPOT_NEAR away is a mark one stands at, not one a shot is wanted from.
    beside = not target.warp and target.kind not in ('explore', 'hunt')
    if beside and math.dist(scaled(target.point), (player.x, player.y)) <= SPOT_NEAR:
        # A press more than the way needed, 3.5 from Nihlathak's spot with him on it (12:56:41 on
        # 2026-10-11): the hop spent a charge, moved nothing, and the step waited 2.3 s for a move
        # with attack mode held back behind it.
        LOG.info('Macro: no hop toward %s: the character is beside it', target.label)
        run.say(f'At {target.label}')
        return
    aspect = rect[2] / rect[3]
    here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    key = (target.area, math.floor(target.point[0]), math.floor(target.point[1]))
    ring = run.pad.ring(TELEPORT) if run.pad is not None else None  # controller mode: a hop of one length
    found = None
    if not far_banned(key, run.clock()):
        way = way_for(target, Viewport(aspect), True)
        found = landing(target, player, way, aspect, ring) if way.from_here(here) < math.inf else None
        if found is None:
            ban_far(key, run.clock())
            LOG.info(
                'Macro: no landing by the far way to %s from (%.1f, %.1f): the near way for %.0fs',
                target.label, player.x, player.y, FAR_DISTRUST,
            )  # fmt: skip
    if found is None:
        way = way_for(target, Viewport(aspect))
        if way.from_here(here) == math.inf:
            raise Abort(f'no way over the rooms to {target.label}')
        found = landing(target, player, way, aspect, ring)
    if found is None:
        raise Abort(f'no footing in view brings the character nearer to {target.label}')
    spot, gain = found
    run.mark('planned')
    if math.dist(scaled(spot), (player.x, player.y)) < MOVED:
        # The best landing is where the character stands (a press more than the way needed, beside
        # Nihlathak at 12:25:45 on 2026-10-11): a hop there shows no move, and the step waited 2.2 s
        # for one with attack mode held back behind it.
        LOG.info('Macro: no hop toward %s: the landing is where the character stands', target.label)
        run.say(f'At {target.label}')
        return
    run.light = light  # a Blade Warp looks for a clear line: the whole game
    if warp is not None and warp(target, player, scaled(spot)):
        return
    run.light = light + 1
    hop_to(run, target, player, rect, spot, gain, key_names)


def hop_to(
    run: Run, target: Target, player: Player, rect: tuple[int, int, int, int], spot: Point, gain: float, key_names
) -> None:
    """The Teleport hop itself, onto the landing `spot` (tiles) chosen for `target`, `gain` tiles off the
    way: the staff in hand if a staff it is, the pointer, the key (also during the cast before), and the
    landing watched for. `player` is the character where the hop starts from. Who chose the landing is
    the caller: the teleport step (`_hop_toward`), or the movement set that teleports (macros/movement.py
    `hop_leg`, made by travel.py `Travel.make`)."""
    aspect = rect[2] / rect[3]
    take_teleport(run, key_names)
    left = math.dist(spot, target.point) * TILE_UNITS
    staff = run.reads.teleport()
    charges = f', {staff.charges} charges' if staff is not None else ''
    run.say(f'Teleport toward {target.label}: {left:.0f} left after this{charges}')
    run.in_time('the hop')  # a hop long after its key is a surprise, not a step
    aim = scaled(spot)
    if run.pad is not None:
        run.pad.aim_place((player.x, player.y), aim)  # controller mode: a heading (macros/pad.py)
    else:
        run.actuator.snap(*ground_fraction(player, *scaled(spot), aspect), scatter=(4, 3))
    press_hop(run, lambda w: w.player is not None and landed_from(w.player, player, aim))
    if target.warp:
        door, entry = scaled(target.point), entry_spot(target)
        LOG.info(
            'Macro: door %s marked at (%.1f, %.1f), entry %s; this hop aims %.1f from the mark',
            target.label, *door,
            'not known yet' if entry is None else '({:.1f}, {:.1f})'.format(*scaled(entry)), math.dist(aim, door),
        )  # fmt: skip
    where = (
        f'aimed at ({aim[0]:.1f}, {aim[1]:.1f}), {math.dist(aim, (player.x, player.y)):.1f} from ({player.x:.1f}, '
        f'{player.y:.1f}), {gain * TILE_UNITS:.1f} off the way, footing {footing(Ground(target.ground), spot)}, '
        f'{len(target.ground)} grids, '
        f'pointer {run.actuator.keys.pointer()} in {rect}'
    )

    def arrived(w) -> bool:
        return w.player is not None and landed_from(w.player, player, aim)

    def unspent() -> bool:
        now = run.reads.teleport()
        return staff is not None and now is not None and now.in_hand and now.charges == staff.charges > 0

    def unlanded() -> bool:
        # Teleport the character's own (OWN_REPRESS): its cast over, the character where the hop began
        now = run.world().player
        return (
            OWN_REPRESS
            and staff is None
            and now is not None
            and not moved(now, player)
            and now.mode not in ACTING
            and now.mode not in KEY_DROP_MODES
        )

    seen = run.seen(arrived, REPRESS_SECONDS, HOP_POLL)
    if seen is None and unspent():
        LOG.info(
            'Macro: teleport %s; nothing %.1fs after the key, no charge spent: pressed again', where, REPRESS_SECONDS
        )
        press_skill(run, TELEPORT, HOP_POLL)
    elif seen is None and unlanded():
        LOG.info(
            "Macro: teleport %s; nothing %.1fs after the key, the character's own Teleport, the character free where "
            'it was: pressed again', where, REPRESS_SECONDS,
        )  # fmt: skip
        press_skill(run, TELEPORT, HOP_POLL)
    now = run.reads.teleport()
    spent = staff is not None and now is not None and now.charges < staff.charges
    if seen is None and spent and not target.warp and math.dist(aim, (player.x, player.y)) <= 2 * SPOT_NEAR:
        # A charge spent on a short hop onto a spot and no move: the spot is taken (above), and the
        # character is as near as it gets. Not waited out with a fight held back behind the step.
        LOG.info('Macro: teleport %s; no move, the charge spent: the spot is taken', where)
        run.say(f'At {target.label}')
        return
    if seen is None and run.seen(arrived, HOP_SECONDS, HOP_POLL) is None:
        after, now = run.world(), run.reads.teleport()
        LOG.info(
            'Macro: teleport %s; the character did not move: key %s, slots %s, staff %s, mode now %s, right skill %s',
            where, run.keys.get(TELEPORT), world_slots(after), now,
            after.player.mode if after.player else None, after.player.right_skill if after.player else None,
        )  # fmt: skip
        if staff is not None and now is not None and now.in_hand and now.charges == staff.charges > 0:
            # The staff in hand, no charge spent: the key cast nothing, twice. The game drops Teleport
            # from its key when a game is left with the staff in hand (user, 2026-10-11; 01:26 that
            # night: three steps in a row, until the key was bound again in the skill list). In a game
            # a hop has landed in the key is not lost.
            if after.game_name in LANDED:
                raise Abort('Teleport: the game took neither of two presses (no charge spent)')
            raise Abort(LOST_KEY)
        raise Abort('Teleport: the character did not move (no charges, nowhere to land?)')
    run.mark('landed')
    LANDED[:] = [run.world().game_name]
    landed = run.world().player
    if landed is not None:
        LANDING[:] = [(landed.x, landed.y, run.clock())]
        herald_pack.hopped(run.clock(), math.dist((player.x, player.y), (landed.x, landed.y)))  # mark REMARK_AFTER_HOP
        off = (landed.x - aim[0], landed.y - aim[1])
        MISSED[:] = [(aim, (landed.x, landed.y), landed.area)] if math.hypot(*off) >= MOVED else []
        LOG.info(
            'Macro: teleport %s; landed at (%.1f, %.1f), off by %.1f (%+.1f, %+.1f)',
            where, landed.x, landed.y, math.hypot(*off), *off,
        )  # fmt: skip
