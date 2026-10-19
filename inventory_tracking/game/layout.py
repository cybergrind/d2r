"""Where the game keeps what the macros read: image addresses and record offsets."""

from inventory_tracking.config import RESOURCE_READER
from inventory_tracking.native.layout import PANEL_FLAGS, SHOW_ITEMS_RVA, UI_PANELS_RVA, WEAPON_SLOTS


SKILL_SLOTS_RVA = 0x1E011B0
SKILL_SLOTS = 16
SKILL_SLOT_SIZE = 28
EMPTY_SLOT = 0xFFFFFFFF
GAME_NAME_RVA = 0x1E9A0B8
GAME_NAME_SIZE = 32
# Research: bytes that moved around the loading screen. None is relied on (0x2122131 and 0x20D7DA0 read wrong
# on the host, 2026-10-06); their changes are logged against the first working summon (routines.LoadTrace).
TRACE_RVAS = (
    0x20D7DA0, 0x25A5C41, 0x2121F39, 0x2121F81, 0x2121FE9, 0x2122011, 0x21220B1, 0x2122131,
    0x19DAB10, 0x1ABD6F1, 0x1AB8A71, 0x1AB8AEC, 0x1E3C410, 0x1E3C7F0, 0x1EC39BE, 0x1EC38EA,
    0x1EB3465, 0x1EB118D, 0x1EC3944, 0x1A7EC19,
)  # fmt: skip
# 255 in a game, 0 while a new game loads, back (254, then 255) when its view comes up and keys are accepted
# (host traces, 2026-10-06). 0x1EB118D moves with it.
VIEW_RVA = 0x1EB3465
# (unit type, unit id) of the unit under the pointer (whole-data search, host 2026-10-10). Unknown with nothing
# under the pointer.
HOVER_RVA = 0x1E010A4
IN_GAME = 0x00  # byte of the panel array: 1 in a game, 0 from Save and Exit to the next game
MONSTER_OWNER = 84  # monster data u32[21]: the owning player's unit id (native/mercenary.py)
MONSTER_DATA = 0x58  # monster data bytes read per live monster: the type flags and the owner lie within
NO_OWNER = 0xFFFFFFFF
# Monster data byte +0x1A (probe logs 2026-10-02/03): 0x08 unique (Heralds too), 0x04 champion, 0x02 super
# unique, 0x10 a minion of one of those (alone). Seen on leaders: 0x08, 0x0c, 0x0a, 0x4c (ghostly champion).
TYPE_FLAGS = 0x1A
SUPER_FLAG, CHAMPION_FLAG, UNIQUE_FLAG = 0x02, 0x04, 0x08
LEADER_FLAGS = SUPER_FLAG | CHAMPION_FLAG | UNIQUE_FLAG
MINION_FLAG = 0x10
# Monster data bytes from +0x20: special modifiers (monumod ids; 0 = none); uniques show 3 in Hell, minions 2.
MODIFIERS = slice(0x20, 0x29)
# Player modes that are an action under way: attacks, casts, skill sequences (classic table; macros/routines.py).
ACTING = frozenset((7, 8, 10, 11, 12, 13, 14, 15, 16, 18))
HERALD_TIER_STAT = 367  # itemstatcost `heraldtier`: on a Terror Zone's Herald and on its minions (terror/tracker.py)
ALIGNMENT_STAT = 172  # non-zero on allies: summons, the mercenary (terror/tracker.py)
# A unit's skill list (third-parties/d2go memory/player.go): pointers to the left/right button skill records,
# each starting with a pointer to its skills.txt record, whose first u16 is the skill id.
SKILL_LIST = 0x100
LEFT_SKILL, RIGHT_SKILL = 0x08, 0x10
PLAYER_UNIT = 0
MONSTER_UNIT = 1
OBJECT_UNIT = 2  # doors among the objects (levels/doors.py)
OBJECT_PATH = 0x18  # an object's static path: x at 0x10, y at 0x14 (loot/ground.py static_position)
MISSILE_UNIT = 3  # blades and bolts in flight (takes/record.py dumps them raw: layout research)
# The unit hash table: twelve slots of 128 heads, the client's six then the "server" six (MapAssist UnitType).
# The player's own missiles hang off the server missile slot, others' off the client one (MapAssist GameMemory.cs).
MISSILE_SLOTS = (3, 9)
UNIT_SLOTS = 12
MISSILE_RECORD = 0x160  # bytes of a missile unit record dumped
MISSILE_PATH = 0x30  # bytes of its path record dumped
# A monster's whole path record (movement research): target point 0x10/0x12, waypoint count 0x34, target unit
# 0x70, waypoints near 0xC8 by the classic layout (client code, 2026-10-11; not checked live).
PATH_RECORD = 0x240
MISSILE_DATA = 0x80  # bytes of its data record (pUnitData) dumped on first sight: skill, velocity, target?
# A missile unit record's owner: unit type, then unit id (tests/.../arena/evidence/blows.py OWNER).
MISSILE_OWNER = 0xE8
DATA_RVA, DATA_SIZE = 0x197A000, 0xC98000  # the image's writable data (record probe)
ITEM_UNIT = 4
TILE_UNIT = 5  # doors: warp tiles, with a static path like an object's
FULL_STATS = 0xE8  # the unit's full stat list (native/units.py describe_player)
EQUIPPED_MODE = 1
ITEM_OWNER, ITEM_BODY_LOCATION = 0x0C, 0x54  # item data (native/units.py describe_item)
# The weapon set in hand; the other set sits at 11 and 12 (config.py: staff 4 -> 11 on swap).
HANDS = frozenset((4, 5))
SWAP_SET = WEAPON_SLOTS - HANDS  # what the other set gives is not the character's while it is not in hand
# An item's full stat list, where a staff's charged skills are (tracking/resources.py select_teleport).
TELEPORT_STATS = RESOURCE_READER.teleport_stats_offset
DEFILER_CLASS = 744
# A unit's state bits, 32 to a word; this word holds states 192-223 (states.txt: `consume` 208 is bit 16,
# `hexpurge` 202 bit 10).
STATE_FLAGS = 0xB48
# Every state word by that layout: states 0-31 six words before STATE_FLAGS, to 224-255 in the one after. Only
# STATE_FLAGS is confirmed; the recorder writes the run raw (takes/record.py `s`) for curses, poison and delays.
STATE_RUN = (STATE_FLAGS - 6 * 4, 8 * 4)
TICK_HEAD = 0x20
HEX_PURGE_BIT = 1 << (202 - 192)
PSYCHIC_WARD_BIT = 1 << (206 - 192)  # states.txt `psychicward`, the aurastate of skill 387
# States 32-63, five words before STATE_FLAGS: `battleorders` 32, `battlecommand` 51 (states.txt; seen in take
# 20261017T204049Z-129).
LOW_STATES = STATE_FLAGS - 5 * 4
BATTLE_ORDERS_BIT = 1 << (32 - 32)
BATTLE_COMMAND_BIT = 1 << (51 - 32)
# State 185 `cooldown` (the word before STATE_FLAGS, states 160-191): the casting delay, set at a delayed skill's
# action frame, cleared when the delay ends (rca/2026-10-13/run-1233-findings.md §3).
COOLDOWN_BIT = 1 << (185 - 160)
LYING_DEAD = 12  # monster mode: dead, the death animation (mode 0) over
# Flags that mean something is open over the game view (the array also holds bytes set with nothing open).
OPEN_PANELS = {name: offset for name, offset in PANEL_FLAGS.items() if name != 'belt_rows'}
SHOW_ITEMS = SHOW_ITEMS_RVA - UI_PANELS_RVA  # the Show Items toggle's byte in the panels' read: 1 on, 0 off


# The only rejuvenation potion worth a belt cell (user, 2026-10-10: "we need a full rejuv potion instead").
FULL_REJUVENATION = 531
# The only healing potion worth one (user, 2026-10-10: "only super hp or full rejuv"); the filter hides the rest.
SUPER_HEALING = 606
GOLD_CLASS = 538  # misc.txt `gld` (items/data/item_metadata.json bases)
GOLD_STAT = 14  # itemstatcost.txt `gold`: a pile's amount
BASE_STATS = 0x30  # the unit's own stat list (terror/monsters.py)
ROLLED_QUALITIES = frozenset((2, 3, 4))  # ItemData quality: normal, superior, magic (loot/shown.py RARITIES)
# The item types whose rolls are read off the ground (items metadata): the Void line's daggers, shields (Monarch),
# Paladin shields (Sacred Targe, Sacred Rondache)
ROLLED_TYPES = frozenset(('knif', 'shie', 'ashd'))


NAME_WRAP = 99  # after it the number starts from 1 again (the player, 2026-10-17: "upon reaching 99, we start from 1")


# Monster modes in which it strikes or casts (monmode.txt: A1 4, A2 5, the cast 7, S1-S4 8-11).
STRIKING_MODES = frozenset((4, 5, 7, 8, 9, 10, 11))
SKILL_IN_USE = 0x18  # in the skill list: the pointer to the skill being used
SKILL_RECORD = 0x50  # bytes of the skill record kept: its row pointer first, the points and base level within


STACK_MOST = 99  # a resource tab's stack at most: the Tal Runes' refused at 99 (the player, 2026-10-17)
SHARED_PAGES = 5  # the shared stash's pages ("Page 1 / 5", macros/stash.py SHARED_PAGES)
ITEM_PAGE = 0x55  # item data: the inventory page byte (native/units.py describe_item; 4 a stash's)
STASH_ITEM_PAGE = 4  # collection/capture.py STASH_PAGE


IDENTIFY_TOME = 534  # Tome of Identify (items metadata `ibk`, 2026-10-17)
CURSOR_MODE = 4  # an item unit's mode on the pointer (0 stored, 1 worn, 2 belt, 3 ground, 4 cursor: D2 item modes)
KEY_STACK = 12  # keys in a stack at most (d2data misc.json `key` maxstack, 2026-10-16)
TOME_CHARGES = 20  # Town Portal charges in the tome at most (misc.json `tbk` maxstack)
KEY_STATS = RESOURCE_READER.key_stats_offset
PORTAL_STATS = RESOURCE_READER.portal_stats_offset
QUALITIES = {1: 'low', 2: 'normal', 3: 'superior', 4: 'magic', 5: 'set', 6: 'rare', 7: 'unique', 8: 'crafted'}


SHOP_GRIDS = (2, 3, 4, 5)  # a vendor's four tabs, in order (shop/capture.py SHOP_GRIDS: the tab is the index - 2)


# The unit's flag word. Bit 0x02 "can be selected": matched objects.txt's selectable-in-mode on 113 objects
# (2026-10-12; unopened chests, jars, shrines). Bit 0x04 was set on unbroken jars only (`IsAttackable0`).
UNIT_FLAGS = 0x124
SELECTABLE_FLAG = 0x02


BANK = 267  # objects.txt `Bank` (*ID), the stash a town's character puts its things in (macros/stash.py)


RESISTS = (39, 41, 43, 45)  # fireresist, lightresist, coldresist, poisonresist (itemstatcost.txt)
DEFENSE_PERCENT = 16  # item_armor_percent: a superior armor's enhanced defense (itemstatcost.txt)


# Stats kept on a layer other than 0 (itemstatcost.txt): item_addclassskills (83, layer = class), item_addskill_tab
# (188, layer = skill tree). Layer 0 alone missed them (a +2 Summoning amulet sold, 2026-10-19 08:17).
LAYERED_SKILLS = (83, 188)
