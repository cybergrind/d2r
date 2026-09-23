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
