"""What a macro knows of the game: the records a look reads."""

from dataclasses import dataclass, field

from inventory_tracking.game.layout import IMMUNE, LEADER_FLAGS, MINION_FLAG, NO_OWNER, STACK_MOST
from inventory_tracking.items.grid import INVENTORY_SIZE, Grid
from inventory_tracking.items.identity import ETHEREAL_FLAG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.stat_constants import StatId
from inventory_tracking.levels.doors import Door
from inventory_tracking.loot.shown import NAMED_QUALITIES
from inventory_tracking.native.layout import BATTLE_ORDERS_SKILL, BELT_SIZE, NONCLASS_SKILL_STAT, TOWN_IDS
from inventory_tracking.tracking.belt import BeltColumns


@dataclass(frozen=True)
class Player:
    unit_id: int
    name: str
    mode: int
    area: int
    x: float  # world units
    y: float
    consume: bool | None  # None when the effect list could not be read
    consume_node: bytes = field(default=b'', compare=False, repr=False)  # research: the buff's record
    left_skill: int | None = None  # the skill on the left mouse button; None when unreadable
    right_skill: int | None = None
    stats_at: int = field(
        default=0, compare=False, repr=False
    )  # the unit's stat list (takes/record.py reads life and mana)
    hex_purge: bool | None = None  # the Hex: Purge buff is on; None when unreadable
    ward: bool | None = None  # Psychic Ward likewise
    record: bytes = field(default=b'', compare=False, repr=False)  # the unit record as read (research)
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw
    # A casting delay runs (state 185, COOLDOWN_BIT): the next delayed skill's key is refused until it clears.
    # None when unreadable (macros/travel.py then times it by the clock).
    cooldown: bool | None = field(default=None, compare=False)
    battle_orders: bool | None = None  # Battle Orders is on; None when unreadable

    @property
    def in_town(self) -> bool:
        return self.area in TOWN_IDS

    @property
    def buffs(self) -> tuple[bool | None, ...]:
        """Psychic Ward, Hex: Purge, Consume (the recorder's `f` order); None for one unread."""
        return (self.ward, self.hex_purge, self.consume)


Bounds = tuple[int, int, int, int]  # a Room2's (x, y, w, h) tiles: the key the level map names rooms by
Stats = tuple[tuple[int, int, int], ...]  # (layer, stat id, raw) of a stat list as read


@dataclass(frozen=True)
class Monster:
    """A monster unit as one walk of the unit table read it: the look's (game/decode.py `monster_table`) or the
    Terror Zone probe's and HUD's (terror/monsters.py `monster_units`, raw data on first sight only). A field the
    walk does not read keeps its default: no owner, no flags, not an ally (hostile is the safe reading)."""

    unit_id: int
    txt_id: int
    mode: int
    x: float
    y: float
    owner: int = NO_OWNER
    flags: int = 0  # type flags (TYPE_FLAGS byte)
    ally: bool = False  # alignment stat set: a summon or the mercenary
    life: int = 0  # whole points (stats 6 and 7); 0 when the stats were unreadable
    max_life: int = 0
    raw: bytes = field(default=b'', compare=False, repr=False)  # unit and monster data, Defilers only
    stats_at: int = field(default=0, compare=False, repr=False)  # the unit's stat list, for a full read
    path: bytes = field(default=b'', compare=False, repr=False)  # the whole path record, on request
    modifiers: tuple[int, ...] = field(default=(), compare=False)  # monumod ids: Lightning Enchanted is 17
    tier: int = field(default=0, compare=False)  # its Herald's tier (stat 367); 0: none
    # (stat, percent) of its resistances (game/layout.py MONSTER_RESISTS) its full stat list holds at the look; a
    # resistance the list does not hold is 0. (): unread
    resists: tuple[tuple[int, int], ...] = field(default=(), compare=False)
    # On request (`records`): the unit record and monster data raw, for unnamed fields (takes/record.py).
    record: bytes = field(default=b'', compare=False, repr=False)
    states: bytes = field(default=b'', compare=False, repr=False)  # state words (STATE_RUN), with `records`
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw, in a striking mode
    # The Terror Zone walk's: the level and Room2 of the path's Room1 (None: unread); on first sight the monster
    # data (hex) and the full and base stat lists.
    area: int | None = None
    room: Bounds | None = None
    data_hex: str | None = None
    stats: Stats | None = None
    base_stats: Stats | None = None
    path_at: int = field(default=0, compare=False)  # dynamic path address: the HUD reads live positions there
    unit_at: int = field(default=0, compare=False)  # unit record address (hud/dots.py)

    @property
    def leader(self) -> bool:
        """A unique, champion or super unique: what the seek step hunts (macros/hunt.py); minions are not."""
        return bool(self.flags & LEADER_FLAGS) and not self.flags & MINION_FLAG

    def resist(self, stat: int) -> int:
        """Its resistance `stat` in percent as read (`resists`); 0 where none was read."""
        return dict(self.resists).get(stat, 0)

    def immune(self, stat: int) -> bool:
        """Whether it takes nothing of that element: its resistance IMMUNE or over."""
        return self.resist(stat) >= IMMUNE


VALUABLE, HEALING, REJUVENATION = 'valuable', 'healing', 'rejuvenation'  # what a drop is to the pickup step
GOLD = 'gold'  # a pile the character takes by standing on it: gone to, never clicked


@dataclass(frozen=True)
class Drop:
    """An item on the ground worth a walk: one the loot marks point at, or a potion the belt may want."""

    unit_id: int
    x: float  # world units
    y: float
    label: str
    kind: str  # VALUABLE, GOLD, HEALING or REJUVENATION
    size: tuple[int, int] = (1, 1)  # inventory cells across and down (loot/data/sizes.json)
    # With no room for a prized drop the pickup press stops; for the rest it warns and goes on. Unknown worth: prized.
    prized: bool = True
    # What found it ('rune', 'material', 'unique', NAMED, 'shown'; '' for gold and potions), its items.txt row and
    # ItemData quality (0 unread), for pickmode.py.
    source: str = ''
    txt: int = 0
    quality: int = 0
    # The base's rolls read off the ground for the bases the loop judges there (pickmode.py); None unread or n/a.
    rolls: Rolls | None = None


# The source of a unique or set item the loot filter shows: a full inventory stops for it (the player, 2026-10-14;
# rca/2026-10-14/run-1214-findings.md §3.1).
NAMED = 'named'


def prized(source: str, *, marked: bool) -> bool:
    """Whether a full inventory stops the pickup press for a drop and a level run stands by it (user, 2026-10-12:
    "allow moving when the item isn't very valuable"): what the loot marks point at, and every unique or set item
    the filter shows (`NAMED`, 2026-10-14). Not the low runes, rings, jewels, gems or shown magic/rare/white gear."""
    return source in ('unique', NAMED) or (source in ('rune', 'material') and marked)


def shown_source(quality: int) -> str:
    """The `prized` source of a shown ground item: `NAMED` for unique or set, else 'shown'."""
    return NAMED if quality in NAMED_QUALITIES else 'shown'


@dataclass(frozen=True)
class Loot:
    """What the pickup step decides on (macros/pickup.py): the drops near the character, its belt and its life."""

    drops: tuple[Drop, ...] = ()
    belt: tuple[int | None, ...] = (None,) * BELT_SIZE  # item class by cell; the first four are the hotkey row
    life: int = 0  # whole points; 0 when unreadable
    max_life: int = 0
    # The inventory's rows, '.' a free cell and '#' a taken one (collection/capture.py grids); None: unread.
    room: tuple[str, ...] | None = None
    stats: tuple[tuple[int, int], ...] = ()  # current set's full stats, already read with life
    game: tuple[str, int] | None = None  # (game name, the character's unit id) the belt is of; None: unread
    # What each belt column last held this game (tracking/belt.py `BeltColumns`, kept by the runner): an emptied
    # healing column stays one; None: the belt alone decides.
    columns: BeltColumns | None = None
    # The Horadric Cube's rows like `room` (grid 5, 3x4: rca/2026-10-13/pickup-cube.md §3). None: unread or no cube.
    cube: tuple[str, ...] | None = None
    # Drops (unit ids) taken only because the filter shows them (loot/shown.py): a level run does not stand by one
    # for want of room. Shown uniques and sets are not among them (`NAMED`).
    shown: frozenset[int] = frozenset()
    # Unit ids in the character's grids now (inventory, cube, stash: `held_items`): how `PutDown` knows own items.
    carried: frozenset[int] = frozenset()
    # (unit id, classid) of drops whose class was read: how `PutDown` knows an item after it gets a new unit id.
    classes: tuple[tuple[int, int], ...] = ()
    # False: a belt item was unreadable and `belt` lacks it: the belt is unknown this look, never empty (no refill,
    # no drink, no empty-belt warning from it; the player, 2026-10-19)
    belt_read: bool = True


@dataclass(frozen=True)
class Teleport:
    """A staff with Teleport charges the character wears, in the set in hand or the other one."""

    charges: int
    maximum: int
    in_hand: bool


@dataclass(frozen=True)
class Wear:
    """The worn item with the least of its durability left: its class, its durability and its maximum."""

    txt: int
    durability: int
    maximum: int

    @property
    def share(self) -> float:
        return self.durability / self.maximum


def least_worn(items) -> Wear | None:
    """Of (class, item flags, full stat list) of the worn items, the one with the least durability share left;
    ethereal (no vendor repairs it) and indestructible ones aside; None with none."""
    found = []
    for txt, flags, stats in items:
        if flags & ETHEREAL_FLAG:
            continue
        values = {stat['id']: stat['raw'] for stat in stats if stat['layer'] == 0}
        most = values.get(StatId.MAX_DURABILITY, 0)
        if most > 0:
            found.append(Wear(txt, min(values.get(StatId.DURABILITY, 0), most), most))
    return min(found, key=lambda wear: wear.share) if found else None


def gives_orders(stats) -> bool:
    """Whether an item's stat list gives Battle Orders as a skill (NONCLASS_SKILL_STAT), as Call to Arms does."""
    return any(stat['id'] == NONCLASS_SKILL_STAT and stat['layer'] == BATTLE_ORDERS_SKILL for stat in stats)


def given_skills(stats) -> frozenset[int]:
    """The skills the items give as the character's own (NONCLASS_SKILL_STAT, the skill its layer: Enigma's
    Teleport (97, 54, 1)), not as charges."""
    return frozenset(stat['layer'] for found in stats for stat in found if stat['id'] == NONCLASS_SKILL_STAT)


@dataclass(frozen=True)
class World:
    in_game: bool
    open_panels: tuple[str, ...]
    game_name: str
    slots: tuple[int | None, ...]  # skill id by slot
    trace: bytes = b''  # research: the bytes at TRACE_RVAS
    view: int = 255  # the byte at VIEW_RVA: 0 while a game loads
    player: Player | None = None
    monsters: tuple[Monster, ...] = ()  # alive, with a position
    doors: tuple[Door, ...] = ()  # door objects streamed around the character, open or closed
    dead: frozenset[int] = frozenset()  # unit ids of monsters lying dead (a kill; a unit merely gone is not)
    show_items: bool | None = None  # the game's Show Items toggle; None: not read

    @property
    def quit_menu(self) -> bool:
        return 'quit_menu' in self.open_panels


@dataclass(frozen=True)
class Carried:
    """An item in the carried inventory (macros/cube.py): its unit, class (items.txt row), top-left cell and size."""

    unit_id: int
    txt: int
    x: int
    y: int
    size: tuple[int, int]
    quality: int = 0  # ItemData quality (0 unread; 4 magic, 6 rare: macros/junk.py)
    identified: bool = True  # the ItemData flag (True when unread, so it is never sent to identify)
    # ItemData +0x34: a unique's uniqueitems.txt row once identified (0 before; 359 Gheed's Fortune)
    unique: int = 0


@dataclass(frozen=True)
class Pack:
    """The carried inventory's items and the Horadric Cube's rows ('.' a free cell; None: no cube read)."""

    items: tuple[Carried, ...] = ()
    cube: tuple[str, ...] | None = None
    cube_items: frozenset[int] = frozenset()  # the units in the cube
    in_cube: tuple[Carried, ...] = ()  # the cube's items, each at its first cell there (macros/stash.py)
    # Keys carried (all stacks) and Town Portal tome charges (tracking/resources.py): None unread, 0 with none.
    keys: int | None = None
    portals: int | None = None
    # A key stack has room (KEY_STACK) or none is carried, so a Shift + right click buys without a new cell; None
    # unread (macros/shop.py).
    key_room: bool | None = None
    # The item on the pointer (CURSOR_MODE), None with none: a click that picked it up instead (macros/stash.py).
    pointer: int | None = None
    # Tome of Identify charges: None unread or no tome, 0 an empty tome (no quantity stat; macros/junk.py).
    identifies: int | None = None
    # The personal stash page's items and rows ('.' free), read whatever panel is open (macros/charms.py).
    stashed: tuple[Carried, ...] = ()
    stash: tuple[str, ...] | None = None

    @property
    def inventory(self) -> Grid:
        """The carried inventory's grid from its items' cells and sizes."""
        return Grid.from_items(self.items, INVENTORY_SIZE)


@dataclass(frozen=True)
class Page:
    """A stash page: 0 personal, 1..5 shared in the owners' +0xD8 order (collection/research.md R1); its 10 x 10
    rows ('.' free), owner unit and item units."""

    index: int
    rows: tuple[str, ...]
    owner: int | None = None
    units: frozenset[int] = frozenset()
    # Its items, each at its first cell, read as the inventory's (`carried_items`; macros/charms.py).
    items: tuple[Carried, ...] = ()

    @property
    def free(self) -> int:
        return sum(row.count('.') for row in self.rows)


@dataclass(frozen=True)
class StashView:
    """The stash in town, panel shut or open (collection/research.md R2): pages and resource-tab stacks by class."""

    pages: tuple[Page, ...]
    stacks: tuple[tuple[int, int], ...] = ()  # (item class, count), sorted

    def count(self, txt: int) -> int:
        return dict(self.stacks).get(txt, 0)

    def room(self, txt: int) -> int:
        """How many more of class `txt` its tab's stack takes."""
        return max(STACK_MOST - self.count(txt), 0)

    def full(self) -> frozenset[int]:
        return frozenset(txt for txt, count in self.stacks if count >= STACK_MOST)

    def page_of(self, unit_id: int) -> int | None:
        """The page the item unit lies on, None on none."""
        return next((page.index for page in self.pages if unit_id in page.units), None)

    def said(self) -> str:
        """`pages free 0:n 1:n …; full stacks <names>` for the log."""
        bases = metadata()['bases']
        names = sorted(bases.get(str(txt), {}).get('name', f'item {txt}') for txt in self.full())
        pages = ' '.join(f'{page.index}:{page.free}' for page in self.pages)
        return f'pages free {pages}; full stacks {", ".join(names) or "none"}'


@dataclass(frozen=True)
class Stocked:
    """An item a vendor sells: its class, the tab (0 Armor ... 3 Misc) and its top-left cell there."""

    txt: int
    tab: int
    x: int
    y: int
    unit_id: int = 0  # what the hover record names under the pointer on it


def _rows(grid: dict | None) -> Grid | None:
    """A grid's rows; None for no grid."""
    return Grid.from_cells(grid) if grid is not None else None


def has_room(rows: tuple[str, ...] | None, size: tuple[int, int]) -> bool:
    """Whether a free block of `size` cells is left in the rows; True when they were not read."""
    return rows is None or Grid(rows).has_room(size)


@dataclass(frozen=True)
class Warp:
    """A door: a warp tile unit of the loaded rooms."""

    unit_id: int
    warp: int  # its lvlwarp Id (levels/presets.warp_box)
    x: float  # world units: the click box's anchor
    y: float


@dataclass(frozen=True)
class Thing:
    """An object a mark names for a click: an object unit of the loaded rooms."""

    unit_id: int
    txt_id: int  # objects.txt id
    mode: int  # 0 until it is operated (a body searched, a chest opened)
    x: float  # world units: the picture's and click box's anchor
    y: float
    selectable: bool | None = field(default=None, compare=False)  # the game's own flag (UNIT_FLAGS); None: unread


@dataclass(frozen=True)
class Rolls:
    """A base's rolls read off the ground (`base_rolls`; itemstatcost.txt ids): sockets (194), single class skills
    as (skill id, level) (107, skill in the layer), enhanced defense (16; None when the item's +0xD0 modifier chain,
    where this build keeps it, was not read whole), the least of the four resistances (39, 41, 43, 45) and the
    ethereal flag; since M5 (2026-10-20) also a superior weapon's enhanced damage (17, the same chain; None with it
    unread) and the skill tab bonuses as (layer, value) (188, layer = class * 8 + tab: a bow's +3 Bow and Crossbow
    Skills automod is layer 0)."""

    sockets: int
    skills: tuple[tuple[int, int], ...] = ()
    defense: int | None = 0
    resists: int = 0
    ethereal: bool = False
    damage: int | None = 0
    tabs: tuple[tuple[int, int], ...] = ()
