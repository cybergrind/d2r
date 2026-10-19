"""Verified facts about the supported game build: identifiers, sizes and scales.

Offsets that gate optional readers stay in `config.RESOURCE_READER`; these values were checked against the
d2data dump, controlled probes or memory dumps and never change at runtime. Evidence: history/layout_notes.md.
"""

# Only this D2R.exe is read; `LiveReader.connect` refuses anything else.
SUPPORTED_SHA256 = '1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7'

# A byte in the loaded image (controlled OFF/ON captures, 2026-09-21).
SHOW_ITEMS_RVA = 0x1EBD164

# Open-panel byte flags (0/1) from this RVA, d2go's OpenMenus layout, anchored by 129 captures of this build
# (2026-09-27, inventory_tracking/history/layout_notes.md). Show Items is +0x0C of the same array.
UI_PANELS_RVA = 0x1EBD158
# ClientTerrorZoneService: a pointer to an object holding the terrorized levels, 16-byte entries (level id
# first) at +0x80, their count at +0x88. From the automap name code (0x140ca6dd9, 2026-10-12); not yet seen live.
TERROR_SERVICE_RVA = 0x1E00508
TERROR_LEVELS, TERROR_LEVEL_COUNT, TERROR_LEVEL_ENTRY = 0x80, 0x88, 0x10
UI_PANELS_SIZE = 0x20
# Input method byte, 1 in controller mode (`ai_d2_g_controller_mode`; rca/2026-10-13/controller-mode.md; not yet
# seen live). `ai_d2_request_input_mode` (0x14064d4e0) sets panel manager +0xDB = 1 and the wanted mode at +0xDC;
# its reload (0x140682f20) sets the byte and clears the flag.
CONTROLLER_MODE_RVA = 0x1EAD337
PANEL_MANAGER_RVA = 0x1EE5790
PANEL_PENDING, PANEL_WANTED = 0xDB, 0xDC
# Controller bindings loaded at game entry: 32 records of 0x1C, skill first (-1: none); the `.ctlo`/`.ctl` body
# (loot-to-cube-mouse.md §2).
CTL_BINDINGS_RVA = 0x1E01370
CTL_RECORD, CTL_RECORDS = 0x1C, 32
# Controller per-player state (`ai_d2_g_controller_state`), a 0xB8 record per player slot (dword at PLAYER_SLOT_RVA):
# +0xD10 the client's target (unit pointer), +0xD44 the pressed button's record, +0xD4C its skill (-1: none).
CTL_STATE_RVA = 0x1F6A030
PLAYER_SLOT_RVA = 0x1EAD46C
CTL_STATE_STRIDE = 0xB8
CTL_TARGET, CTL_PRESSED_RECORD, CTL_PRESSED_SKILL = 0xD10, 0xD44, 0xD4C
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
# item_nonclassskill (itemstatcost.txt): another class's skill the item gives, skill id as layer (Enigma's
# Teleport: (97, 54, 1), live capture 2026-10-17)
NONCLASS_SKILL_STAT = 97
BATTLE_ORDERS_SKILL = 149  # skills.txt: what Call to Arms gives (97, 149, n)
TELEPORT_SKILL = 54
LIFE_FRACTION_MAX = 32768

# Act 2 hireling (monstats) and the animation modes that mean dead or dying.
HIRELING_CLASS_ID = 338
DEAD_MODES = frozenset((0, 12))
# A player unit dying and lying dead; the corpse it leaves on the level is a player unit of its own, lying dead.
CORPSE_MODE = 17
PLAYER_DEAD_MODES = frozenset((0, CORPSE_MODE))

# Belt: sixteen cells, four hotkey columns, items in mode 2 with path y == 0.
BELT_SIZE = 16
BELT_COLUMNS = 4
BELT_ITEM_MODE = 2

# Equipped weapon body locations including the swap set; town area IDs per act.
WEAPON_SLOTS = frozenset((4, 5, 11, 12))
TOWN_IDS = frozenset((1, 40, 75, 103, 109))

# Level/room chain (Win+C dumps 2026-09-30, inventory_tracking/history/layout_notes.md "Level rooms"):
# Path +0x20 Room1, Room1 +0x18 Room2, Room2 +0x90 level, level +0x1F8 area ID; level +0x10 first Room2,
# Room2 +0x48 next; Room2 +0x40 -> struct whose first u32 is the LvlPrest Def; Room2 +0x60 x, y, width,
# height as u32 tiles (5 world units per tile).
PATH_ROOM1 = 0x20
ROOM1_ROOM2 = 0x18
ROOM2_LEVEL = 0x90
LEVEL_AREA_ID = 0x1F8
LEVEL_FIRST_ROOM2 = 0x10
ROOM2_NEXT = 0x48
ROOM2_PRESET = 0x40
ROOM2_BOUNDS = 0x60
TILE_UNITS = 5

# Room2 neighbours (dump 20260930T124726Z-e166c530): +0x10 an array of Room2 pointers, +0x18 its count
# (5-9, the room included); at the level edge the extra entries are the adjacent level's Room2s.
ROOM2_NEAR = 0x10
ROOM2_NEAR_COUNT = 0x18

# Room1 (loaded room) neighbours and collision (dump 20260930T135418Z-6b2890e1): Room1 +0x00 near-room array,
# +0x40 its count; +0x38 the collision grid: +0x00 x, y, width, height in sub-tiles (Room2 bounds x5), +0x20 a
# width x height u16 mask. Bit 0x1 blocks walking.
ROOM1_NEAR = 0x00
ROOM1_NEAR_COUNT = 0x40
ROOM1_COLLISION = 0x38
COLLISION_BOUNDS = 0x00
COLLISION_MASK = 0x20
COLLISION_BLOCK_WALK = 0x0001
# Stops a missile (D2MOO COLLIDE_BLOCK_MISSILE); empirical, Catacombs takes of 2026-10-10 (combat/plan.md).
COLLISION_BLOCK_MISSILE = 0x0004
COLLISION_DOOR = 0x0800  # a door unit stands on the cell (D2MOO COLLIDE_DOOR)

# Preset object behind each Room2 preset record (10 Win+C dumps, 2026-09-30): record +0x08 -> object with +0x00
# the Def again, +0x04 the DS1 file index (< lvlprest Files), +0x18 x, y, w, h of the whole preset in tiles.
# Large presets are 8x8 Room2 chunks sharing this one object.
PRESET_RECORD_OBJECT = 0x08
PRESET_OBJECT_FILE = 0x04
PRESET_OBJECT_BOUNDS = 0x18

# Object data (unit +0x10 for objects; dump 20260930T121835Z-713d7e8a): +0x08 the shrine type byte (d2data
# shrines.json; 14 = Stamina, 18 = Gem), +0x10 a shrine txt pointer, set only for shrines (aligned on this build,
# +0x0C in MapAssist's packed struct).
OBJECT_SHRINE_TYPE = 0x08
OBJECT_SHRINE_TABLE = 0x10
