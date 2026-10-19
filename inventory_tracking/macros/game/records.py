"""What a macro knows of the game: the records a look reads (moved from macros/world.py)."""

from dataclasses import dataclass, field

from inventory_tracking.items.grid import INVENTORY_SIZE, Grid
from inventory_tracking.items.identity import ETHEREAL_FLAG
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.stat_constants import StatId
from inventory_tracking.levels.doors import Door
from inventory_tracking.loot.shown import NAMED_QUALITIES
from inventory_tracking.macros.game.layout import LEADER_FLAGS, MINION_FLAG, STACK_MOST
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
    )  # the unit's stat list (combat/record.py reads life and mana)
    hex_purge: bool | None = None  # the Hex: Purge buff is on the character; None when unreadable
    ward: bool | None = None  # Psychic Ward likewise
    record: bytes = field(default=b'', compare=False, repr=False)  # the unit record as read (research)
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw (`skill_in_use`)
    # A casting delay runs on the character (state 185, COOLDOWN_BIT): the next delayed skill's key is
    # refused until it clears. None when unreadable (macros/travel.py then times the delay by the clock).
    cooldown: bool | None = field(default=None, compare=False)
    battle_orders: bool | None = None  # Battle Orders (Call to Arms) is on the character; None when unreadable

    @property
    def in_town(self) -> bool:
        return self.area in TOWN_IDS

    @property
    def buffs(self) -> tuple[bool | None, ...]:
        """The buffs this reader knows of, in the order the combat recorder writes them (record.py `f`):
        Psychic Ward, Hex: Purge, Consume; None for one that could not be read."""
        return (self.ward, self.hex_purge, self.consume)


@dataclass(frozen=True)
class Monster:
    unit_id: int
    txt_id: int
    mode: int
    x: float
    y: float
    owner: int
    flags: int = 0  # type flags (TYPE_FLAGS byte)
    ally: bool = False  # alignment stat set: a summon or the mercenary
    life: int = 0  # whole points (stats 6 and 7); 0 when the stats were unreadable
    max_life: int = 0
    raw: bytes = field(default=b'', compare=False, repr=False)  # unit and monster data, Defilers only
    stats_at: int = field(default=0, compare=False, repr=False)  # the unit's stat list, for a full read
    path: bytes = field(default=b'', compare=False, repr=False)  # the whole path record, on request (PATH_RECORD)
    modifiers: tuple[int, ...] = field(default=(), compare=False)  # monumod ids: Lightning Enchanted is 17
    tier: int = field(default=0, compare=False)  # the tier of the Herald it is or follows (stat 367); 0: none
    # On request (`records`): the unit record and the monster data as this walk read them, for the fields
    # nobody has named yet (the animation frame, the skill in use: combat/record.py `records.jsonl`).
    record: bytes = field(default=b'', compare=False, repr=False)
    states: bytes = field(default=b'', compare=False, repr=False)  # its state words (STATE_RUN), with `records`
    skill: bytes = field(default=b'', compare=False, repr=False)  # the skill in use, raw, in a striking mode

    @property
    def leader(self) -> bool:
        """A unique, champion or super unique: what the seek step hunts (macros/hunt.py); minions are not."""
        return bool(self.flags & LEADER_FLAGS) and not self.flags & MINION_FLAG


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
    size: tuple[int, int] = (1, 1)  # cells across and down it takes in the inventory (loot/data/sizes.json)
    # One the loot marks point at (`prized`): with no room for it the pickup press stops; for the rest it
    # warns and goes on. True unless the read says otherwise: a drop of unknown worth stops the press.
    prized: bool = True
    # What found it (`prized`: 'rune', 'material', 'unique', NAMED, 'shown'; '' for gold and potions), its item class
    # (items.txt row, the unit's txt id; 0 unread) and ItemData quality (0 unread): the pickup mode's (pickmode.py)
    source: str = ''
    txt: int = 0
    quality: int = 0
    # The base's rolls read off the ground (`rolled`) for the bases the loop judges there (pickmode.py `void_base`,
    # `shield_base`); None unread or of another item
    rolls: Rolls | None = None


# The source of a unique or set item the loot filter shows (unidentified, or of any size): one a full inventory
# stops for, as for what the marks point at (the player, 2026-10-14: run-1214-findings.md §3.1).
NAMED = 'named'


def prized(source: str, *, marked: bool) -> bool:
    """Whether a drop is one a full inventory stops the pickup press for, and a level run stands by (user,
    2026-10-12: "allow moving when the item isn't very valuable"): what the loot marks point at — a rune from the
    marks' minimum up, a unique or set item worth a mark, a material of the marks — and every unique or set item
    the loot filter shows (`NAMED`, the player's ruling of 2026-10-14: the run walked past a Unique Plate Mail
    with the inventory full and the player fetched it by hand, rca/2026-10-14/run-1214-findings.md §3.1). Not
    what the pickup takes besides: the low runes, every ring and jewel, the gems and the magic, rare and white
    equipment the loot filter shows."""
    return source in ('unique', NAMED) or (source in ('rune', 'material') and marked)


def shown_source(quality: int) -> str:
    """The source (`prized`) of a ground item the loot filter shows, by its quality: a unique or set one is
    `NAMED`, the rest (magic, rare, white and gray) 'shown'."""
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
    # What each belt column last held this game (tracking/belt.py `BeltColumns`), as the runner keeps it
    # (`BeltKept`): an emptied healing column stays one; None: the belt alone decides.
    columns: BeltColumns | None = None
    # The Horadric Cube's rows as `room` has the inventory's (grid 5, 3x4: rca/2026-10-13/pickup-cube.md §3); read
    # with the panels closed, wherever the cube is. None: unread, or no cube. Not yet a place the pickup puts
    # anything (that is the cube work of pickup-cube.md §6): it is said where a drop has no room in the inventory.
    cube: tuple[str, ...] | None = None
    # The drops (unit ids) taken only because the loot filter shows them (loot/shown.py): magic, rare and white
    # equipment nothing the marks or the pickup's own rules name. A level run does not stand by one for want of room
    # (the player, 2026-10-12: "allow moving when the item isn't very valuable"). A unique or set one the filter shows
    # is not among them: it is prized (`NAMED`, the player, 2026-10-14).
    shown: frozenset[int] = frozenset()
    # The unit ids of the items in the character's grids now (the inventory, the cube, the stash tabs: `held_items`),
    # read with `room`: what `PutDown` knows the player's own items by.
    carried: frozenset[int] = frozenset()
    # (unit id, item class: the game's classid) of the drops whose class was read: what `PutDown` knows an item by
    # once the game has given it a new unit id
    classes: tuple[tuple[int, int], ...] = ()


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
    """Of (class, item flags, full stat list) of the worn items, the one with the least share of its durability left;
    an ethereal one aside (no vendor repairs it), and one without a maximum (indestructible); None with none."""
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
    """The skills the items' stat lists give as skills of the character's own (NONCLASS_SKILL_STAT, the skill its
    layer: Enigma's "+1 to Teleport" (97, 54, 1), the Sling's Town Portal (97, 411, 1)), not as charges."""
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
    dead: frozenset[int] = frozenset()  # unit ids of the monsters lying dead (a kill, where a unit only gone is not)
    show_items: bool | None = None  # the game's Show Items toggle (item labels on the ground); None: not read

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
    identified: bool = True  # the ItemData flag (True unread: an item of unknown state is never identified)
    # ItemData +0x34: a unique's row in uniqueitems.txt once identified (0 before: loot/ground.py; 359 Gheed's Fortune)
    unique: int = 0


@dataclass(frozen=True)
class Pack:
    """The carried inventory's items and the Horadric Cube's rows ('.' a free cell; None: no cube read)."""

    items: tuple[Carried, ...] = ()
    cube: tuple[str, ...] | None = None
    cube_items: frozenset[int] = frozenset()  # the units in the cube
    in_cube: tuple[Carried, ...] = ()  # the cube's items, each at its first cell there (macros/stash.py)
    # The keys carried (every stack) and the Town Portal tome's charges (tracking/resources.py, the same stat at the
    # same offset): None when unread, 0 with none (macros/shop.py restocks under 3)
    keys: int | None = None
    portals: int | None = None
    # Whether a key stack has room for more (KEY_STACK) or none is carried: a Shift + right click on her key fills it
    # (macros/shop.py), where with every stack full it would take a cell for a new one; None when unread
    key_room: bool | None = None
    # The unit id of the item on the pointer (an item unit in CURSOR_MODE), None with none: a click meant to send an
    # item somewhere that took it up instead (macros/stash.py)
    pointer: int | None = None
    # The Tome of Identify's charges (the same stat as the Town Portal tome's): None unread or no tome (macros/junk.py)
    identifies: int | None = None
    # The personal stash page's items and rows ('.' free), read whatever panel is open (macros/charms.py)
    stashed: tuple[Carried, ...] = ()
    stash: tuple[str, ...] | None = None

    @property
    def inventory(self) -> Grid:
        """The carried inventory's grid from its items' cells and sizes."""
        return Grid.from_items(self.items, INVENTORY_SIZE)


@dataclass(frozen=True)
class Page:
    """A stash page (macros/town-plan.md §2.1): 0 the personal one, 1..5 the shared ones in the owners' +0xD8 order
    (collection/research.md R1); its 10 x 10 rows ('.' a free cell), its owner unit and the item units on it."""

    index: int
    rows: tuple[str, ...]
    owner: int | None = None
    units: frozenset[int] = frozenset()
    # Its items, each at its first cell (row by row) with its quality, identified flag and unique row as the inventory's
    # are read (`carried_items`): a Gheed's Fortune taken back from a shared page by a Ctrl + click on its cell
    # (macros/charms.py)
    items: tuple[Carried, ...] = ()

    @property
    def free(self) -> int:
        return sum(row.count('.') for row in self.rows)


@dataclass(frozen=True)
class StashView:
    """The stash as memory holds it in town, its panel shut or open (collection/research.md R2): the pages, and the
    resource tabs' stacks by item class (a class not held has no unit: count 0)."""

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
    unit_id: int = 0  # the item's unit: what the game's record names under the pointer on it


def _rows(grid: dict | None) -> Grid | None:
    """A grid's rows; None for no grid."""
    return Grid.from_cells(grid) if grid is not None else None


def has_room(rows: tuple[str, ...] | None, size: tuple[int, int]) -> bool:
    """Whether a free block of `size` cells is left in the rows; True when they were not read (the pickup sites')."""
    return rows is None or Grid(rows).has_room(size)


@dataclass(frozen=True)
class Warp:
    """A door: a warp tile unit of the loaded rooms."""

    unit_id: int
    warp: int  # its lvlwarp Id (levels/presets.warp_box)
    x: float  # world units: what the door's click box hangs from
    y: float


@dataclass(frozen=True)
class Thing:
    """An object a mark names for a click: an object unit of the loaded rooms."""

    unit_id: int
    txt_id: int  # objects.txt id
    mode: int  # 0 until it is operated (a body searched, a chest opened)
    x: float  # world units: what its picture and click box hang from
    y: float
    selectable: bool | None = field(default=None, compare=False)  # the game's own flag (UNIT_FLAGS); None: unread


@dataclass(frozen=True)
class Rolls:
    """A base's rolls read off the ground (`base_rolls`): its sockets (stat 194), single class skills ((skill id,
    level): stat 107, the skill in its layer: a dagger's Warlock staff mods), enhanced defense (stat 16), the least of
    its four resistances (stats 39, 41, 43, 45: a Paladin shield's all-resistance roll) and the ethereal flag.
    Items/stat_constants.py `StatId`; the stat ids checked in pricing/raw/game-excel/itemstatcost.txt."""

    sockets: int
    skills: tuple[tuple[int, int], ...] = ()
    defense: int = 0
    resists: int = 0
    ethereal: bool = False
