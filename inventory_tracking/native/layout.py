"""Verified facts about the supported game build: identifiers, sizes and scales.

Memory offsets that gate optional readers stay in `config.RESOURCE_READER`; this
module holds values that were checked against the d2data dump or controlled
probes on 2026-09-21 and never change at runtime.
"""

# Only this D2R.exe is read; `LiveReader.connect` refuses anything else.
SUPPORTED_SHA256 = '1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7'

# Controlled 2026-09-21 OFF/ON/OFF/ON and new-game OFF/ON captures.
# A byte in the loaded image, not the old UI panel-offset interpretation.
SHOW_ITEMS_RVA = 0x1EBD164

# Open-panel byte flags (0/1) starting at this RVA; d2go's OpenMenus layout anchored
# by 129 captured images of this build (layout_notes.md, 2026-09-27): inventory +0x01
# set in every hover attachment, NPC interact/shop +0x08/+0x0B only in the 31 vendor
# captures, stash +0x18 only in the 23 stash-session attachments (always with the
# inventory), cube +0x19 in the cube captures, mercenary +0x1E in the one mercenary
# panel capture. The Show Items byte above is +0x0C of the same array.
UI_PANELS_RVA = 0x1EBD158
UI_PANELS_SIZE = 0x20
PANEL_FLAGS = {
    'inventory': 0x01,
    'character': 0x02,
    'skill_select': 0x03,
    'skill_tree': 0x04,
    'chat': 0x05,
    'npc_interact': 0x08,
    'quit_menu': 0x09,
    'npc_shop': 0x0B,
    'anvil': 0x0D,
    'quest_log': 0x0E,
    'waypoint': 0x13,
    'stash': 0x18,
    'cube': 0x19,
    'belt_rows': 0x1A,
    'mercenary': 0x1E,
}

# Potion class IDs (misc.json): rejuvenation / full rejuvenation, minor..super healing.
REJUVENATION_POTIONS = frozenset((530, 531))
HEALING_POTIONS = frozenset((602, 603, 604, 605, 606))
IDENTIFY_TOME_CLASS_ID = 534  # Tome of Identify; d2data misc.json, maxstack 20 (2026-09-23).
TOME_CLASS_ID = 533  # Tome of Town Portal
KEY_CLASS_ID = 558  # Ordinary Key; d2data misc.json, maxstack 12 (2026-09-21).
STAFF_CLASS_IDS = frozenset((63, 64, 65, 66, 67, 91, 92, 156, 157, 158, 159, 160, 259, 260, 261, 262, 263))

# Unit stat IDs (layer 0) and the client-side life scale for monsters.
LIFE_STAT = 6
MAX_LIFE_STAT = 7
QUANTITY_STAT = 70
CHARGED_SKILL_STAT = 204
TELEPORT_SKILL = 54
LIFE_FRACTION_MAX = 32768

# Act 2 hireling (monstats) and the animation modes that mean dead or dying.
HIRELING_CLASS_ID = 338
DEAD_MODES = frozenset((0, 12))

# Belt: sixteen cells, four hotkey columns, items in mode 2 with path y == 0.
BELT_SIZE = 16
BELT_COLUMNS = 4
BELT_ITEM_MODE = 2

# Equipped weapon body locations including the swap set; town area IDs per act.
WEAPON_SLOTS = frozenset((4, 5, 11, 12))
TOWN_IDS = frozenset((1, 40, 75, 103, 109))

# Level/room chain. Confirmed 2026-09-30 by two Win+C dumps in Arcane Sanctuary
# (runs/level/, layout_notes.md "Level rooms"): the LvlPrest 527 room predicted from
# the entrance held the Summoner and the Journal. Path +0x20 Room1, Room1 +0x18 Room2,
# Room2 +0x90 level, level +0x1F8 area ID; level +0x10 first Room2, Room2 +0x48 next;
# Room2 +0x40 points at a struct whose first u32 is the LvlPrest Def; Room2 +0x60 holds
# x, y, width, height as u32 tiles (5 world units per tile).
PATH_ROOM1 = 0x20
ROOM1_ROOM2 = 0x18
ROOM2_LEVEL = 0x90
LEVEL_AREA_ID = 0x1F8
LEVEL_FIRST_ROOM2 = 0x10
ROOM2_NEXT = 0x48
ROOM2_PRESET = 0x40
ROOM2_BOUNDS = 0x60
TILE_UNITS = 5

# Room2 neighbours. Confirmed 2026-09-30 in Win+C dump 20260930T124726Z-e166c530 (Lower Kurast):
# +0x10 points at an array of Room2 pointers, +0x18 is its count (5-9, the room itself included);
# for 80/80 rooms every entry was a Room2 of the level except at the level edge, where the extra
# entries are Room2s of the adjacent level (their level pointer and area are not in that dump).
ROOM2_NEAR = 0x10
ROOM2_NEAR_COUNT = 0x18

# Room1 (loaded room) neighbours and collision. Room1 +0x00 near-room array, +0x40 its count (the
# research walk over loaded rooms, levels/research.py). Confirmed 2026-09-30 in Win+C dump
# 20260930T135418Z-6b2890e1 (Cave 2, 8 of 9 rooms): Room1 +0x38 points at the collision grid,
# grid +0x00 holds x, y, width, height in sub-tiles (the Room2 bounds x5) and +0x20 points at a
# width x height u16 mask. Bit 0x1 blocks walking: drawn out, the set cells were the cave's
# walls and the clear ones its corridors (other bits: 0x4, 0x20, and 0x8000/0x200/0x400 where
# units stood).
ROOM1_NEAR = 0x00
ROOM1_NEAR_COUNT = 0x40
ROOM1_COLLISION = 0x38
COLLISION_BOUNDS = 0x00
COLLISION_MASK = 0x20
COLLISION_BLOCK_WALK = 0x0001
# Stops a missile (D2MOO COLLIDE_BLOCK_MISSILE). Empirical, Catacombs takes of 2026-10-10 11:44 UTC
# (combat/plan.md): the recorded blades crossed 931 cells of 0x0001 alone 148 times and the 26.8k
# cells with 0x0004 set 26 times (7 at door units whose state had changed since the masks were read).
COLLISION_BLOCK_MISSILE = 0x0004
COLLISION_DOOR = 0x0800  # a door unit stands on the cell (D2MOO COLLIDE_DOOR)

# Preset object behind each Room2 preset record. Confirmed 2026-09-30 across 10 Win+C dumps
# (Arcane, Tower Cellar 1, Halls of Pain, Halls of Vaught): record +0x08 points at an object
# whose +0x00 repeats the Def, +0x04 is the DS1 file index (always < lvlprest Files when
# Files > 0: 0/1 for two-file presets, 3 of 4 for Vaught's Nihl*), +0x18 x, y, w, h is the
# whole preset's bounds in tiles (Temple quadrants 40x40, the Vaught level 84x84). Large
# presets are split into 8x8 Room2 chunks that all share this one object.
PRESET_RECORD_OBJECT = 0x08
PRESET_OBJECT_FILE = 0x04
PRESET_OBJECT_BOUNDS = 0x18

# Object data (unit +0x10 for objects). Confirmed 2026-09-30 by a Win+C dump next to a shrine the
# user identified as a Stamina Shrine (20260930T121835Z-713d7e8a): +0x08 is the shrine type byte
# (d2data shrines.json code; 14 = Stamina, 18 = Gem), +0x10 a shrine txt pointer that is set only
# for shrines. MapAssist's byte-packed struct puts that pointer at +0x0C; on this build it is aligned.
OBJECT_SHRINE_TYPE = 0x08
OBJECT_SHRINE_TABLE = 0x10
