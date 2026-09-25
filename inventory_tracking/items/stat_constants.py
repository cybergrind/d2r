"""Native stat encodings; market property IDs remain a separate namespace."""

from enum import IntEnum


class StatId(IntEnum):
    MIN_DAMAGE = 21
    MAX_DAMAGE = 22
    SECONDARY_MIN_DAMAGE = 23
    SECONDARY_MAX_DAMAGE = 24
    DEFENSE = 31
    BASE_SPEED = 68
    QUANTITY = 70
    DURABILITY = 72
    MAX_DURABILITY = 73
    CLASS_SKILLS = 83
    ELEMENTAL_SKILLS = 126
    MAGIC_MASTERY = 357
    SINGLE_SKILL = 97
    CLASS_SINGLE_SKILL = 107
    FLEE = 112
    AURA = 151
    SKILL_TAB = 188
    SOCKETS = 194
    CHARGES = 204
    SELF_REPAIR = 252
    REPLENISH_QUANTITY = 253


TOTAL_LABELS = {
    StatId.MIN_DAMAGE: 'Minimum damage',
    StatId.MAX_DAMAGE: 'Maximum damage',
    StatId.SECONDARY_MIN_DAMAGE: 'Secondary minimum damage',
    StatId.SECONDARY_MAX_DAMAGE: 'Secondary maximum damage',
    StatId.DEFENSE: 'Defense',
    StatId.QUANTITY: 'Quantity',
    StatId.DURABILITY: 'Durability',
    StatId.MAX_DURABILITY: 'Maximum durability',
    StatId.SOCKETS: 'Sockets',
}
CLASS_NAMES = ('Amazon', 'Sorceress', 'Necromancer', 'Paladin', 'Barbarian', 'Druid', 'Assassin', 'Warlock')
CLASS_ABBREVIATIONS = dict(zip(('ama', 'sor', 'nec', 'pal', 'bar', 'dru', 'ass', 'war'), CLASS_NAMES, strict=True))
SKILL_LEVEL_BITS = 6
SKILL_LEVEL_MASK = (1 << SKILL_LEVEL_BITS) - 1
CHARGE_COUNT_BITS = 8
CHARGE_COUNT_MASK = (1 << CHARGE_COUNT_BITS) - 1
CHARGE_PAYLOAD_MAX = (1 << (2 * CHARGE_COUNT_BITS)) - 1
PROC_ENCODING = 2
PROC_DESCRIPTION_FUNCTION = 15
PERCENT_MAX = 100
REPAIR_RATE_SCALE = 100
TOTAL_STATS_DESCRIPTOR_OFFSET = 0xE8

# Native stat188 layers: class * 8 + tree, verified by pinned d2go stat descriptions.
SKILL_TABS = (
    ('Bow and Crossbow Skills', 'Passive and Magic Skills', 'Javelin and Spear Skills'),
    ('Fire Skills', 'Lightning Skills', 'Cold Skills'),
    ('Curses', 'Poison and Bone Skills', 'Summoning Skills'),
    ('Combat Skills', 'Offensive Auras', 'Defensive Auras'),
    ('Combat Skills', 'Masteries', 'Warcries'),
    ('Summoning Skills', 'Shape Shifting Skills', 'Elemental Skills'),
    ('Traps', 'Shadow Disciplines', 'Martial Arts'),
    # RotW skilldesc SkillPage 1/2/3; layer57 observed on Dread Edge.
    ('Demon Skills', 'Eldritch Skills', 'Chaos Skills'),
)

FLEE_SCALE = 128  # properties.json howl: percentage divided by 128.

# d2data itemstatcost/properties/uniqueitems: sunder properties use func1=1,
# a native magnitude of 300, and a text-only tooltip (not a boolean flag).
SUNDER_STATS = frozenset({187, 189, 190, 191, 192, 193})
SUNDER_MAGNITUDE = 300

# D2MOO D2Combat.h D2C_ElementTypes; D2Skills.cpp indexes elemskill by nEType.
SKILL_ELEMENTS = {1: 'Fire', 2: 'Lightning', 3: 'Magic', 4: 'Cold', 5: 'Poison'}
