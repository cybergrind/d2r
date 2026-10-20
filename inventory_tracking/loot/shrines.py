"""Shrine type names (object data +0x08, native/layout.py OBJECT_SHRINE_TYPE)."""

# d2data shrines.json 'Code' order (checked 2026-09-30); 18 = Gem Shrine.
SHRINE_NAMES = (
    'None', 'Refilling Shrine', 'Health Shrine', 'Mana Shrine', 'Health Exchange Shrine',
    'Mana Exchange Shrine', 'Armor Shrine', 'Combat Shrine', 'Resist Fire Shrine', 'Resist Cold Shrine',
    'Resist Lightning Shrine', 'Resist Poison Shrine', 'Skill Shrine', 'Mana Recharge Shrine',
    'Stamina Shrine', 'Experience Shrine', 'Enirhs Shrine', 'Portal Shrine', 'Gem Shrine', 'Fire Shrine',
    'Monster Shrine', 'Exploding Shrine', 'Poison Shrine',
)  # fmt: skip
GEM_SHRINE = 18
# d2data shrines.json Code 15 'Experience Shrine' (checked 2026-10-20): a Booster, Arg0 50 (% more experience from
# kills), 'Duration in frames' 3600, no 'reset time in minutes' (every other booster has 5): it is used once and never
# comes back. states.json `shrine_experience` is state 137; the shrine states (128-137) have no `group`.
EXPERIENCE_SHRINE = 15
EXPERIENCE_STATE = 137
EXPERIENCE_SECONDS = 3600 * 0.04  # 144 s: 3600 frames of 25 a second (macros/hunting/base.py FRAME)
# objects.txt classes that are shrines (d2data objects.json SubClass bit 1, checked 2026-10-20: 92 classes; the Stamina
# Shrine of dump 20260930T121835Z-713d7e8a was class 83). A shrine's type byte is read only on these.
SHRINE_CLASSES = frozenset((
    2, 77, 81, 83, 84, 85, 86, 93, 96, 97, 109, 116, 120, 123, 124, 133, 134, 135, 136, 150, 151, 164, 165, 166, 167,
    168, 170, 172, 173, 184, 190, 191, 197, 199, 200, 201, 202, 206, 226, 231, 232, 236, 249, 260, 262, 263, 264, 265,
    275, 276, 277, 278, 279, 280, 281, 282, 299, 300, 301, 302, 303, 319, 320, 325, 343, 344, 361, 415, 416, 422, 423,
    424, 428, 429, 465, 466, 473, 480, 484, 485, 489, 492, 493, 496, 498, 500, 504, 510, 513, 521, 522, 523,
))  # fmt: skip
