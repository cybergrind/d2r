"""Where the game keeps what the macros read: image addresses and record offsets (moved from macros/world.py)."""

from inventory_tracking.config import RESOURCE_READER
from inventory_tracking.native.layout import PANEL_FLAGS, SHOW_ITEMS_RVA, UI_PANELS_RVA, WEAPON_SLOTS


SKILL_SLOTS_RVA = 0x1E011B0
SKILL_SLOTS = 16
SKILL_SLOT_SIZE = 28
EMPTY_SLOT = 0xFFFFFFFF
GAME_NAME_RVA = 0x1E9A0B8
GAME_NAME_SIZE = 32
# Research: bytes that moved around the loading screen in the one recording. The two tried as
# "loading" (0x2122131) and "playable" (0x20D7DA0) both read wrong in loaded games on the host
# (2026-10-06), so none is relied on; their changes are logged against the moment the first
# summon works (routines.LoadTrace) to find one that really marks a playable game.
TRACE_RVAS = (
    0x20D7DA0, 0x25A5C41, 0x2121F39, 0x2121F81, 0x2121FE9, 0x2122011, 0x21220B1, 0x2122131,
    0x19DAB10, 0x1ABD6F1, 0x1AB8A71, 0x1AB8AEC, 0x1E3C410, 0x1E3C7F0, 0x1EC39BE, 0x1EC38EA,
    0x1EB3465, 0x1EB118D, 0x1EC3944, 0x1A7EC19,
)  # fmt: skip
# 255 in a game, 0 while a new game loads, back (254, then 255) when its view comes up: 6.5 s
# after Enter in the recording and 6.2 s and 6.6 s in two traced host runs (2026-10-06), where
# the first key was accepted. 0x1EB118D moves with it.
VIEW_RVA = 0x1EB3465
# (unit type, unit id) of the unit under the pointer: the one address the whole-data search found holding
# the item's pair on each of the pickup step's first five clicks (host, 18:46-18:54 on 2026-10-10), on
# three levels and two games. What it holds with nothing under the pointer is not known.
HOVER_RVA = 0x1E010A4
IN_GAME = 0x00  # byte of the panel array: 1 in a game, 0 from Save and Exit to the next game
MONSTER_OWNER = 84  # monster data u32[21]: the owning player's unit id (native/mercenary.py)
MONSTER_DATA = 0x58  # monster data bytes read per live monster: the type flags and the owner lie within
NO_OWNER = 0xFFFFFFFF
# Monster data byte +0x1A (terror/tracker.py, probe logs 2026-10-02/03): 0x08 unique (Heralds too),
# 0x04 champion, 0x02 super unique, 0x10 a minion of one of those.
TYPE_FLAGS = 0x1A
# Monster data bytes from +0x20: its special modifiers (monumod ids; 0 = none), the enchantments of a
# unique and what its minions inherit (terror/tracker.py FIRST_MODIFIER, MODIFIER_SLOTS).
MODIFIERS = slice(0x20, 0x29)
LEADER_FLAGS = 0x02 | 0x04 | 0x08
MINION_FLAG = 0x10
HERALD_TIER_STAT = 367  # itemstatcost `heraldtier`: on a Terror Zone's Herald and on its minions (terror/tracker.py)
ALIGNMENT_STAT = 172  # non-zero on allies: summons, the mercenary (terror/tracker.py)
# A unit's skill list (third-parties/d2go memory/player.go; the Defiler dump of 2026-10-09 holds a heap
# pointer there): pointers to the skill records on the left and right mouse button, each starting
# with a pointer to its skills.txt record, whose first u16 is the skill id.
SKILL_LIST = 0x100
LEFT_SKILL, RIGHT_SKILL = 0x08, 0x10
MONSTER_UNIT = 1
OBJECT_UNIT = 2  # doors among the objects (levels/doors.py)
OBJECT_PATH = 0x18  # an object's static path: x at 0x10, y at 0x14 (loot/ground.py static_position)
MISSILE_UNIT = 3  # blades and bolts in flight (combat/record.py dumps them raw: layout research)
# The unit hash table has twelve slots of 128 heads (MapAssist UnitType): the client's six, then the
# "server" six; the player's own missiles hang off the server missile slot, other units' off the
# client one (MapAssist GameMemory.cs: Missile and ServerMissile both hold type 3 units). The first
# Chaos Sanctuary take (2026-10-09) found slot 3 empty through 237 casts.
MISSILE_SLOTS = (3, 9)
UNIT_SLOTS = 12
MISSILE_RECORD = 0x160  # bytes of a missile unit record dumped
MISSILE_PATH = 0x30  # bytes of its path record dumped
# A monster's whole path record, for the movement research (combat/plan.md): after the position come
# the target point (0x10, 0x12), the waypoint count (0x34), the target unit (0x70) and, by the classic
# layout, the waypoints near 0xC8 (read from the client's code 2026-10-11; not yet checked live).
PATH_RECORD = 0x240
MISSILE_DATA = 0x80  # bytes of its data record (pUnitData) dumped on first sight: skill, velocity, target?
# A missile unit record's owner: its unit type, then its unit id (tests/.../arena/evidence/blows.py OWNER: 1,771 of
# 1,866 records of take 20261012T065226Z-130 hold a unit id of the take there and nowhere else).
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
# The state bits of a unit, 32 to a word: tracking/consume.py reads state 208 (states.txt `consume`)
# as bit 16 of this word, so it holds states 192-223, and state 202 (`hexpurge`, the aurastate of skill
# 389) is its bit 10. Read from the tables on 2026-10-11; not yet seen to change in the game.
STATE_FLAGS = 0xB48
# Every state word of a unit, as that reading has them laid out: states 0-31 in the first word, six
# words before STATE_FLAGS, to 224-255 in the one after it. Only the word at STATE_FLAGS is confirmed;
# the recorder writes the whole run raw (combat/record.py `s`), for a curse on the character
# (states.txt `amplifydamage` 9, `ironmaiden` 55, `decrepify` 60, `lowerresist` 61), poison (2) and a
# skill's delay to be read off it once a take shows them change.
STATE_RUN = (STATE_FLAGS - 6 * 4, 8 * 4)
TICK_HEAD = 0x20
HEX_PURGE_BIT = 1 << (202 - 192)
PSYCHIC_WARD_BIT = 1 << (206 - 192)  # states.txt `psychicward`, the aurastate of skill 387
# States 32-63, five words before STATE_FLAGS by the layout above (seen: take 20261017T204049Z-129, BC's 51 on 0.3 s
# after its key and BO's 32 0.35 s after its, 23:41:01 on 2026-10-17):
# states.txt `battleorders` 32 and `battlecommand` 51, the aurastates of skills 149 and 155 (Call to Arms)
LOW_STATES = STATE_FLAGS - 5 * 4
BATTLE_ORDERS_BIT = 1 << (32 - 32)
BATTLE_COMMAND_BIT = 1 << (51 - 32)
# State 185 `cooldown`, in the word before STATE_FLAGS (states 160-191): the character's casting delay. Set at
# a delayed skill's action frame and cleared when its delay is over: for Blade Warp 0.20 s after the key and
# 0.80 s long, 64 warps of 64 in the take of 12:33 on 2026-10-13 (rca/2026-10-13/run-1233-findings.md §3).
# Read with STATE_FLAGS in one read.
COOLDOWN_BIT = 1 << (185 - 160)
LYING_DEAD = 12  # monster mode: dead, the death animation (mode 0) over
# Flags that mean something is open over the game view; the array also holds bytes that are
# set with nothing open (Show Items, belt rows and unnamed ones).
OPEN_PANELS = {name: offset for name, offset in PANEL_FLAGS.items() if name != 'belt_rows'}
SHOW_ITEMS = SHOW_ITEMS_RVA - UI_PANELS_RVA  # the Show Items toggle's byte in the panels' read: 1 on, 0 off


# The only rejuvenation potion worth a belt cell (user, 2026-10-10: "we need a full rejuv potion
# instead"); a plain one (530) lay where fourteen clicks could not take it (host, 19:37).
FULL_REJUVENATION = 531
# The only healing potion worth one (user, 2026-10-10: "only super hp or full rejuv"): the smaller sizes
# were gone for, and the loot filter hides them, so no click took them (host, 20:12 and 20:13).
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


# The unit's flag word. Bit 0x02 is "can be selected": Glacial Trail and Drifter Cavern, 09:30 on
# 2026-10-12, 113 object units of 21 classes: set on each of the 15 that objects.txt calls selectable in
# their mode (unopened chests, jars, shrines, a well, the evil urn), clear on the 98 others (the same
# chests and jars once opened, torches, fog, bubbles). Bit 0x04 was set on the unbroken jars only
# (`IsAttackable0`).
UNIT_FLAGS = 0x124
SELECTABLE_FLAG = 0x02


# The objects the run reads (`GameMemory.things`): those a level's mark may name for a click (levels/model.py), the
# town portal the character opens (macros/portal.py), the waypoints (macros/waypoint.py) and every container, which a
# camp's mark opens whatever class the game rolled (macros/teleport.py USES; rca/2026-10-16/loop-first-game-findings.md
# §1: the run read the mark's own id, 1000, and never the chest at it). The combat recorder writes them (`operated`).
BANK = 267  # objects.txt `Bank` (*ID), the stash a town's character puts its things in (macros/stash.py)


RESISTS = (39, 41, 43, 45)  # fireresist, lightresist, coldresist, poisonresist (itemstatcost.txt)
DEFENSE_PERCENT = 16  # item_armor_percent: a superior armor's enhanced defense (itemstatcost.txt)


# Stats an item keeps on a layer other than 0 (itemstatcost.txt): item_addclassskills (83, the layer the class),
# item_addskill_tab (188, the layer the skill tree). Read on layer 0 alone they were missing: a rare amulet with +2 to
# Summoning Skills was sold at 08:17 on 2026-10-19 (keepers.py's "+2 skills" never saw them)
LAYERED_SKILLS = (83, 188)
