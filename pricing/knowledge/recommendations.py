"""Reviewed local leveling advice, deliberately separate from source mentions.

The review table selects advice; it is not a prose classifier. Game facts resolve
identity and eligibility separately. Rebuild with ``python -m
pricing.knowledge.recommendations`` after exporting item facts.
"""

import hashlib
import json
from pathlib import Path


CLASSES = ('amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock')
# Benefit summaries reviewed against timestamped local transcript candidates.
# Numeric values are supplied by the independently verified item-facts layer.
TRANSCRIPT_REVIEW_DATES = dict.fromkeys(['The Spirit Shroud', "Sigon's Sabot", "Sigon's Wrap"], '2026-09-26')

GENERAL = {
    "Sigon's Sabot": 'Movement and cold resistance; attack-rating and magic-find set bonuses are conditional.',
    "Sigon's Wrap": 'Life and fire resistance for early survival; a supporting set piece.',
    'The Spirit Shroud': 'Cannot Be Frozen alternative with an all-skills bonus for progression.',
    "Hsarus' Iron Stay": 'Life and cold resistance for early survival.',
    "Hsarus' Iron Heel": 'Movement speed and fire resistance; attack-rating set bonus is conditional.',
    "Berserker's Headgear": 'Fire resistance for early survival.',
    'Infernal Cranium': 'All resistances for early survival.',
    "Sander's Paragon": 'Magic find for finding leveling equipment; a farming option.',
    "Sander's Taboo": 'Life for survival; attack speed helps attack builds only.',
    "Sander's Riprap": 'Fast movement and attributes; attack rating helps attacks only.',
    "Vidala's Fetlock": 'Movement speed; weigh the strength investment.',
    "Cow King's Hooves": 'Movement speed, dexterity and magic find.',
    'Telling of Beads': 'Skills and resistances for progression.',
    "Iratha's Coil": 'Fire and lightning resistance for survival.',
    "Tal Rasha's Fine-Spun Cloth": 'Mana and magic find for progression or farming.',
    "Bul-Kathos' Wedding Band": 'Skills and life for later progression.',
    'Dwarf Star': 'Life and fire protection when cast rate is covered elsewhere.',
    "Duriel's Shell": 'Resistances, life and cannot be frozen for survival.',
    "Moser's Blessed Circle": 'Resistances and customizable sockets for survival.',
    'Rockstopper': 'Resistances, recovery and physical damage reduction.',
    'Infernostride': 'Movement and fire resistance for progression.',
    'The Stone of Jordan': 'Skills and mana for skill-based builds.',
    'String of Ears': 'Physical damage reduction for survival; life leech helps attacks only.',
    'Peasant Crown': 'Skills, movement and attributes for leveling.',
    'Nightsmoke': 'Mana and resistances for progression.',
    'Duskdeep': 'Resistances and damage reduction for early survival.',
    'Treads of Cthon': 'Movement and life for early progression.',
    'The Eye of Etlich': 'All skills benefits casters too; leech and cold damage apply to attacks.',
    'Tarnhelm': 'All skills and magic find for early progression.',
    'Nokozan Relic': 'Fire resistance and recovery for dangerous fire encounters.',
    'Gorefoot': 'Movement speed for early progression.',
    'Bloodfist': 'Life and hit recovery for early survival.',
    'Nagelring': 'Magic find for early farming; attack rating helps attacks only.',
    'Pelta Lunata': 'Early vitality, energy and strength with blocking.',
    "Biggin's Bonnet": 'Life and mana for very early progression.',
}
CASTER = {
    "Trang-Oul's Claws": 'Faster cast rate and cold resistance for caster progression.',
    'Lidless Wall': 'Skills, cast rate and mana after kills; cover resistances elsewhere.',
    'Suicide Branch': 'Cast rate, skills, life and resistances; compare your cast breakpoint.',
    'Skin of the Vipermagi': 'Skills, cast rate and resistances for caster progression.',
    'Razorswitch': 'Caster skills, cast rate and defensive stats if better alternatives are unavailable.',
    'Spectral Shard': 'Cast rate, mana and resistances; account for dexterity investment.',
    'Magefist': 'Faster cast rate for casters; fire-skill bonus only benefits relevant skills.',
    'Maelstrom': 'Early cast rate and lightning resistance; usable by casters beyond Necromancer.',
}
MELEE = {
    "Death's Guard": 'Cannot be frozen for attack builds.',
    "Death's Hand": 'Attack speed and resistances with the paired belt.',
    "Sigon's Visor": 'Conditional set attack rating for attack builds.',
    "Sigon's Gage": 'Conditional set attack speed for attack builds.',
    "Magnus' Skin": 'Attack speed, attack rating and fire resistance for attack builds.',
    'Crushflange': 'Crushing blow for attacking bosses.',
    'Knell Striker': 'Crushing blow for attacking bosses.',
    "The Cat's Eye": 'Attack speed, movement and dexterity for attack builds.',
    'Raven Frost': 'Cannot be frozen, dexterity and attack rating for attack builds.',
}
RESTRICTED = {
    'The Oculus': ('sorceress', 'caster', 'Sorceress skills and caster utility; consider the teleport-on-hit effect.'),
    "Arreat's Face": ('barbarian', 'melee', 'Barbarian skills and combat utility for progression.'),
    'Homunculus': ('necromancer', 'caster', 'Necromancer skills and resistances for progression.'),
    "Jalal's Mane": ('druid', 'general', 'Druid skills and defensive utility for progression.'),
    'Herald of Zakarum': ('paladin', 'general', 'Paladin skills and defensive utility for progression.'),
    "Titan's Revenge": ('amazon', 'melee', 'Amazon javelin skills for javelin progression.'),
}
CONDITIONS = {
    "Sigon's Sabot": [
        'Requires 70 Strength in its original base; weigh that investment against lighter leveling boots.',
        "With 2 pieces of Sigon's Complete Steel the boots add attack rating; 3 pieces are required for magic find. "
        'Movement and cold resistance work on the boots alone.',
    ],
    "Sigon's Wrap": [
        'Requires 60 Strength in its original base; compare with lower-requirement belts.',
        'Life and fire resistance are standalone; its per-level defense bonus needs a second Sigon piece.',
    ],
    'The Spirit Shroud': [
        'Useful when Cannot Be Frozen is not already covered; '
        'compare the armor slot against resistance and cast-rate alternatives.',
        'The source mentions this as an alternative, not a preferred complete leveling setup.',
    ],
    "Death's Hand": [
        "Equip Death's Guard as the second Death's Disguise piece for the recommended attack-speed bonus."
    ],
    "Hsarus' Iron Heel": [
        "Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). "
        'Movement and fire resistance are standalone.'
    ],
    "Sigon's Visor": ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-rating bonus."],
    "Sigon's Gage": ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-speed bonus."],
    'Magefist': ['Fire-skill bonus is conditional on using fire skills; cast rate remains useful to other casters.'],
    'Dwarf Star': ['Use when your required faster-cast-rate breakpoint is already covered.'],
    'Lidless Wall': ['Cover resistances in other equipment.'],
    'Razorswitch': ['Two-handed staff prevents equipping a shield; compare available alternatives.'],
}
GAPS = {
    "Sander's Superstition": 'Incidental mention without evaluated utility.',
    "Cow King's Horns": 'Collective set endorsement without individual utility review.',
    "Cow King's Hide": 'Collective set endorsement without individual utility review.',
}

# Exact cached guide selections reviewed on 2026-09-23. New mentions are never
# admitted by a keyword heuristic; changed locators need another review.
GUIDE_SOURCE_SHA256 = {
    'leveling-assassin': '548d7b8483f02428f7ebe5be5ac8f0f2e00d10fa2387292c085bba3c4941853b',
    'leveling-barbarian': 'b83f0f5b1d3601577d20aa35bf285b87f9eaa700b11af922321c7de076f6c7d6',
    'leveling-druid': '7b8d388deb56021c517f60d0f6385583eca5d00fe6111fecf62c433f1604760a',
    'leveling-paladin': '284adcd129cd42c0867dce4792102832b537fd2861b3a56e26e203a8af05220c',
    'leveling-amazon': '928aa47e197f786f002ec34997219ef33228aa986090ca9281d44d322eadd749',
    'leveling-necromancer': 'a447a857cfc20421a9fa6531c94b083576dd50f14d460dd549558440854ff844',
    'leveling-sorceress': 'aef55f953d6e1f96d60d6479e2b94d24e8ba88f46fc5d6de1c21fa40b3707b96',
    'leveling-warlock': '201e5010f374ef9126a1c3ccc62b4fe49f4f1f015935bee8713498744a8596d8',
}
GUIDE_SOURCE_NAMES = {
    ('barbarian', "Mara's Kaleidoscope", 'after-level-31-respec-header/item/144@(86, 2409)'): 'Maras Kaleidoscope',
    ('druid', "Mara's Kaleidoscope", 'essentials-header/item/84@(79, 1507)'): 'Maras Kaleidoscope',
    ('necromancer', "Mara's Kaleidoscope", 'essentials-header/item/85@(74, 1112)'): 'Maras Kaleidoscope',
    ('paladin', "Mara's Kaleidoscope", 'after-level-18-respec:-header/item/100@(82, 3003)'): 'Maras Kaleidoscope',
    ('sorceress', "Mara's Kaleidoscope", 'essentials-header/item/82@(77, 893)'): 'Maras Kaleidoscope',
    ('amazon', 'Raven Frost', 'essentials-header/item/101@(78, 1322)'): 'Ravenfrost',
    ('assassin', 'Raven Frost', 'essentials-header/item/89@(77, 804)'): 'Ravenfrost',
    ('assassin', "Mara's Kaleidoscope", 'essentials-header/item/95@(77, 2873)'): 'Maras Kaleidoscope',
}
GUIDE_REVIEW = (
    ('barbarian', "Mara's Kaleidoscope", 'after-level-31-respec-header/item/144@(86, 2409)'),
    ('druid', "Mara's Kaleidoscope", 'essentials-header/item/84@(79, 1507)'),
    ('necromancer', "Mara's Kaleidoscope", 'essentials-header/item/85@(74, 1112)'),
    ('paladin', "Mara's Kaleidoscope", 'after-level-18-respec:-header/item/100@(82, 3003)'),
    ('sorceress', "Mara's Kaleidoscope", 'essentials-header/item/82@(77, 893)'),
    ('necromancer', 'Homunculus', 'essentials-header/item/91@(74, 2103)'),
    ('amazon', 'Raven Frost', 'essentials-header/item/101@(78, 1322)'),
    ('amazon', 'The Stone of Jordan', 'essentials-header/item/108@(78, 3222)'),
    ('amazon', 'The Eye of Etlich', 'essentials-header/item/109@(78, 3815)'),
    ('amazon', "The Cat's Eye", 'essentials-header/item/110@(78, 3883)'),
    ('amazon', "Highlord's Wrath", 'essentials-header/item/111@(78, 3956)'),
    ('barbarian', 'Skin of the Vipermagi', 'after-level-31-respec-header/item/141@(86, 1482)'),
    ('barbarian', 'Magefist', 'after-level-31-respec-header/item/142@(86, 1635)'),
    ('barbarian', 'The Eye of Etlich', 'after-level-31-respec-header/item/143@(86, 2330)'),
    ('barbarian', 'The Stone of Jordan', 'after-level-31-respec-header/item/147@(86, 2851)'),
    ('barbarian', "Arreat's Face", 'after-level-31-respec-header/item/148@(86, 3173)'),
    ('paladin', 'The Eye of Etlich', 'after-level-18-respec:-header/item/99@(82, 2924)'),
    ('paladin', 'The Stone of Jordan', 'after-level-18-respec:-header/item/103@(82, 3445)'),
    ('druid', 'The Eye of Etlich', 'essentials-header/item/83@(79, 1428)'),
    ('druid', 'The Stone of Jordan', 'essentials-header/item/87@(79, 1949)'),
    ('druid', 'Lidless Wall', 'essentials-header/item/89@(79, 2332)'),
    ('druid', "Jalal's Mane", 'essentials-header/item/91@(79, 2563)'),
    ('barbarian', "Death's Hand", 'until-level-31-header/item/138@(86, 225)'),
    ('barbarian', "Death's Guard", 'until-level-31-header/item/139@(86, 294)'),
    ('barbarian', 'Bloodfist', 'until-level-31-header/item/140@(86, 781)'),
    ('paladin', "Death's Hand", 'until-level-18:-header/item/91@(82, 464)'),
    ('paladin', "Death's Guard", 'until-level-18:-header/item/92@(82, 533)'),
    ('paladin', 'Bloodfist', 'until-level-18:-header/item/93@(82, 1030)'),
    ('assassin', 'Raven Frost', 'essentials-header/item/89@(77, 804)'),
    ('assassin', "Mara's Kaleidoscope", 'essentials-header/item/95@(77, 2873)'),
    ('assassin', 'The Stone of Jordan', 'essentials-header/item/93@(77, 2092)'),
    ('assassin', 'The Eye of Etlich', 'essentials-header/item/94@(77, 2794)'),
    ('assassin', 'Skin of the Vipermagi', 'essentials-header/item/99@(77, 3346)'),
    ('assassin', 'Magefist', 'essentials-header/item/100@(77, 3738)'),
    ('assassin', "Death's Hand", 'essentials-header/item/86@(77, 80)'),
    ('assassin', "Death's Guard", 'essentials-header/item/87@(77, 149)'),
    ('assassin', 'Twitchthroe', 'essentials-header/item/92@(77, 1518)'),
    ('druid', 'Spectral Shard', 'essentials-header/item/78@(79, 80)'),
    ('druid', 'Suicide Branch', 'essentials-header/item/79@(79, 149)'),
    ('druid', 'Skin of the Vipermagi', 'essentials-header/item/81@(79, 384)'),
    ('druid', 'Magefist', 'essentials-header/item/82@(79, 537)'),
    ('paladin', 'Spectral Shard', 'after-level-18-respec:-header/item/94@(82, 1734)'),
    ('paladin', 'Suicide Branch', 'after-level-18-respec:-header/item/95@(82, 1803)'),
    ('paladin', 'Skin of the Vipermagi', 'after-level-18-respec:-header/item/97@(82, 2038)'),
    ('paladin', 'Magefist', 'after-level-18-respec:-header/item/98@(82, 2191)'),
    ('assassin', "Hsarus' Iron Heel", 'essentials-header/item/90@(77, 1027)'),
    ('assassin', "Sander's Riprap", 'essentials-header/item/91@(77, 1103)'),
    ('barbarian', "Hsarus' Iron Heel", 'after-level-31-respec-header/item/145@(86, 2495)'),
    ('barbarian', "Sander's Riprap", 'after-level-31-respec-header/item/146@(86, 2571)'),
    ('druid', "Hsarus' Iron Heel", 'essentials-header/item/85@(79, 1593)'),
    ('druid', "Sander's Riprap", 'essentials-header/item/86@(79, 1669)'),
    ('paladin', "Hsarus' Iron Heel", 'after-level-18-respec:-header/item/101@(82, 3089)'),
    ('paladin', "Sander's Riprap", 'after-level-18-respec:-header/item/102@(82, 3165)'),
    ('amazon', "Cow King's Hooves", 'essentials-header/item/112@(78, 4158)'),
    ('amazon', "Cow King's Hide", 'essentials-header/item/113@(78, 4231)'),
    ('amazon', "Cow King's Horns", 'essentials-header/item/114@(78, 4306)'),
    ('amazon', "Titan's Revenge", 'essentials-header/item/106@(78, 2053)'),
    ('amazon', "Death's Hand", 'essentials-header/item/97@(78, 80)'),
    ('amazon', "Death's Guard", 'essentials-header/item/98@(78, 149)'),
    ('amazon', "Hsarus' Iron Heel", 'essentials-header/item/104@(78, 1719)'),
    ('amazon', "Sander's Riprap", 'essentials-header/item/105@(78, 1795)'),
    ('amazon', 'Twitchthroe', 'essentials-header/item/107@(78, 2816)'),
    ('sorceress', 'Skin of the Vipermagi', 'essentials-header/item/79@(77, 80)'),
    ('sorceress', 'Magefist', 'essentials-header/item/80@(77, 233)'),
    ('sorceress', 'The Eye of Etlich', 'essentials-header/item/81@(77, 814)'),
    ('sorceress', "Hsarus' Iron Heel", 'essentials-header/item/83@(77, 979)'),
    ('sorceress', "Sander's Riprap", 'essentials-header/item/84@(77, 1055)'),
    ('sorceress', 'The Stone of Jordan', 'essentials-header/item/85@(77, 1248)'),
    ('sorceress', 'Lidless Wall', 'essentials-header/item/87@(77, 1645)'),
    ('necromancer', 'Skin of the Vipermagi', 'essentials-header/item/82@(74, 80)'),
    ('necromancer', 'Magefist', 'essentials-header/item/83@(74, 233)'),
    ('necromancer', 'The Eye of Etlich', 'essentials-header/item/84@(74, 1033)'),
    ('necromancer', "Hsarus' Iron Heel", 'essentials-header/item/86@(74, 1198)'),
    ('necromancer', "Sander's Riprap", 'essentials-header/item/87@(74, 1274)'),
    ('necromancer', 'The Stone of Jordan', 'essentials-header/item/88@(74, 1554)'),
    ('warlock', "Hsarus' Iron Heel", 'essentials-header/item/47@(90, 80)'),
    ('warlock', "Sander's Riprap", 'essentials-header/item/48@(90, 156)'),
    ('warlock', 'The Stone of Jordan', 'essentials-header/item/49@(90, 414)'),
    ('warlock', 'The Eye of Etlich', 'essentials-header/item/50@(90, 1008)'),
)
COW_KING_PIECES = ("Cow King's Hooves", "Cow King's Hide", "Cow King's Horns")
CASTER_LEVELING_ITEMS = ('Spectral Shard', 'Suicide Branch', 'Skin of the Vipermagi', 'Magefist')
GUIDE_ARCHETYPES = {(cls, name): ('caster',) for cls in ('druid', 'paladin') for name in CASTER_LEVELING_ITEMS}
EARLY_MELEE_RESPECS = {'barbarian': 31, 'paladin': 18}
GUIDE_ARCHETYPES.update(
    {(cls, name): ('melee',) for cls in EARLY_MELEE_RESPECS for name in ("Death's Hand", "Death's Guard")}
)
GUIDE_REVIEW_DATES = {
    (cls, name): '2026-09-26' for cls in EARLY_MELEE_RESPECS for name in ("Death's Hand", "Death's Guard", 'Bloodfist')
}
# Reviewed caster leveling options; source sections retain their respec scope.
CASTER_TAIL_ITEMS = (
    ('barbarian', 'Skin of the Vipermagi'),
    ('barbarian', 'Magefist'),
    ('barbarian', 'The Eye of Etlich'),
    ('barbarian', 'The Stone of Jordan'),
    ('barbarian', "Arreat's Face"),
    ('paladin', 'The Eye of Etlich'),
    ('paladin', 'The Stone of Jordan'),
    ('druid', 'The Eye of Etlich'),
    ('druid', 'The Stone of Jordan'),
    ('druid', 'Lidless Wall'),
    ('druid', "Jalal's Mane"),
)
GUIDE_ARCHETYPES.update(dict.fromkeys(CASTER_TAIL_ITEMS, ('caster',)))
GUIDE_REVIEW_DATES.update(dict.fromkeys(CASTER_TAIL_ITEMS, '2026-09-26'))
LEVELING_JEWELRY_TAIL = (
    ('barbarian', "Mara's Kaleidoscope"),
    ('druid', "Mara's Kaleidoscope"),
    ('necromancer', "Mara's Kaleidoscope"),
    ('paladin', "Mara's Kaleidoscope"),
    ('sorceress', "Mara's Kaleidoscope"),
    ('necromancer', 'Homunculus'),
    ('amazon', 'Raven Frost'),
    ('amazon', 'The Stone of Jordan'),
    ('amazon', 'The Eye of Etlich'),
    ('amazon', "The Cat's Eye"),
    ('amazon', "Highlord's Wrath"),
)
GUIDE_REVIEW_DATES.update(dict.fromkeys(LEVELING_JEWELRY_TAIL, '2026-09-26'))
GUIDE_ARCHETYPES.update({key: ('caster',) for key in LEVELING_JEWELRY_TAIL if key[0] != 'amazon'})
GUIDE_PRIORITY = {
    **{(cls, name): 3 for cls in ('druid', 'paladin') for name in ('Spectral Shard', 'Suicide Branch')},
    **{('amazon', name): 3 for name in COW_KING_PIECES},
    **{(cls, "Hsarus' Iron Heel"): 3 for cls in CLASSES},
}
MOVEMENT_BOOTS = ("Hsarus' Iron Heel", "Sander's Riprap")
BOOT_GUIDE_CONDITIONS = {
    'barbarian': ('The cited guide recommendation is in the after level 31 respec setup.',),
    'paladin': ('The cited guide recommendation is in the after level 18 respec setup.',),
}
GUIDE_BENEFITS = {
    ('barbarian', "Mara's Kaleidoscope"): (
        'Later leveling amulet option for all skills, resistances and attributes.',
        [
            'Available from item requirement level 67; guide progression stages do not override equip requirements.',
            'Compare class/tree skill amulets and the full cast-rate and resistance setup; '
            'optional if already available.',
            'The source places this option after the level 31 caster respec.',
        ],
    ),
    ('druid', "Mara's Kaleidoscope"): (
        'Later leveling amulet option for all skills, resistances and attributes.',
        [
            'Available from item requirement level 67; guide progression stages do not override equip requirements.',
            'Compare class/tree skill amulets and the full cast-rate and resistance setup; '
            'optional if already available.',
        ],
    ),
    ('necromancer', "Mara's Kaleidoscope"): (
        'Later leveling amulet option for all skills, resistances and attributes.',
        [
            'Available from item requirement level 67; guide progression stages do not override equip requirements.',
            'Compare class/tree skill amulets and the full cast-rate and resistance setup; '
            'optional if already available.',
        ],
    ),
    ('paladin', "Mara's Kaleidoscope"): (
        'Later leveling amulet option for all skills, resistances and attributes.',
        [
            'Available from item requirement level 67; guide progression stages do not override equip requirements.',
            'Compare class/tree skill amulets and the full cast-rate and resistance setup; '
            'optional if already available.',
            'The source places this option after the level 18 caster respec.',
        ],
    ),
    ('sorceress', "Mara's Kaleidoscope"): (
        'Later leveling amulet option for all skills, resistances and attributes.',
        [
            'Available from item requirement level 67; guide progression stages do not override equip requirements.',
            'Compare class/tree skill amulets and the full cast-rate and resistance setup; '
            'optional if already available.',
        ],
    ),
    ('necromancer', 'Homunculus'): (
        '+2 to Necromancer Skills and resistances support caster leveling.',
        [
            'Available from item requirement level 42; guide progression stages do not override equip requirements.',
            'The guide says all skills; native definitions establish Necromancer skills plus Curses skills.',
            'Compare Splendor and shield alternatives; plan block investment and cover the full defensive setup.',
        ],
    ),
    ('amazon', 'Raven Frost'): (
        'Cannot Be Frozen alternative for Amazon leveling.',
        [
            'Available from item requirement level 45; guide progression stages do not override equip requirements.',
            "Allows replacing Rhyme with Ancient's Pledge for resistance coverage when the full "
            'setup permits; compare ring slots and attack-speed needs.',
        ],
    ),
    ('amazon', 'The Stone of Jordan'): (
        'All skills and mana support Amazon skill-based leveling.',
        [
            'Available from item requirement level 29; guide progression stages do not override equip requirements.',
            'Optional if already available; compare Cannot Be Frozen, mana sustain and the complete gear setup.',
        ],
    ),
    ('amazon', 'The Eye of Etlich'): (
        'Early unique skill-amulet alternative for Amazon leveling.',
        [
            'Available from item requirement level 15; guide progression stages do not override equip requirements.',
            'Compare Amazon skill amulets, attack-speed breakpoints and resistances.',
        ],
    ),
    ('amazon', "The Cat's Eye"): (
        'Attack speed, movement and dexterity support Amazon leveling.',
        [
            'Available from item requirement level 50; guide progression stages do not override equip requirements.',
            'Compare the complete javelin attack-speed breakpoint and actual shield/dexterity requirements.',
        ],
    ),
    ('amazon', "Highlord's Wrath"): (
        'Skills, attack speed and lightning resistance provide a later Amazon leveling amulet option.',
        [
            'Available from item requirement level 65; guide progression stages do not override equip requirements.',
            'Deadly Strike improves eligible physical attack damage, not Lightning Fury lightning '
            'damage; compare the complete attack-speed breakpoint.',
        ],
    ),
    ('barbarian', 'Skin of the Vipermagi'): (
        'Preferred caster leveling armor for cast rate, skills and resistances.',
        [
            'The cited guide recommendation is in the after level 31 respec setup.',
            'Compare the complete cast-rate breakpoint and resistance coverage; verify equip requirements.',
        ],
    ),
    ('barbarian', 'Magefist'): (
        'Cast-rate gloves for War Cry leveling.',
        [
            'The cited guide recommendation is in the after level 31 respec setup.',
            'The fire-skill bonus does not increase War Cry; compare the total cast-rate '
            'breakpoint and equip requirements.',
        ],
    ),
    ('barbarian', 'The Eye of Etlich'): (
        'Unique skill-amulet alternative for caster leveling.',
        [
            'The cited guide recommendation is in the after level 31 respec setup.',
            'Compare against class-skill or relevant skill-tree amulets and verify equip requirements.',
        ],
    ),
    ('barbarian', 'The Stone of Jordan'): (
        'All skills support spell damage for caster leveling.',
        [
            'The cited guide recommendation is in the after level 31 respec setup.',
            'Use if already available; compare the complete cast-rate, mana and defensive setup.',
        ],
    ),
    ('barbarian', "Arreat's Face"): (
        'Barbarian skills and resistances provide helmet utility for War Cry leveling.',
        [
            'The cited guide recommendation is in the after level 31 respec setup.',
            'The attack rating does not improve War Cry; compare spell skills, cast-rate '
            'alternatives and equip requirements.',
        ],
    ),
    ('paladin', 'The Eye of Etlich'): (
        'Unique skill-amulet alternative for caster leveling.',
        [
            'The cited guide recommendation is in the after level 18 respec setup.',
            'Compare against class-skill or relevant skill-tree amulets and verify equip requirements.',
        ],
    ),
    ('paladin', 'The Stone of Jordan'): (
        'All skills support spell damage for caster leveling.',
        [
            'The cited guide recommendation is in the after level 18 respec setup.',
            'Use if already available; compare the complete cast-rate, mana and defensive setup.',
        ],
    ),
    ('druid', 'The Eye of Etlich'): (
        'Unique skill-amulet alternative for caster leveling.',
        ['Compare against class-skill or relevant skill-tree amulets and verify equip requirements.'],
    ),
    ('druid', 'The Stone of Jordan'): (
        'All skills support spell damage for caster leveling.',
        ['Use if already available; compare the complete cast-rate, mana and defensive setup.'],
    ),
    ('druid', 'Lidless Wall'): (
        'Caster shield alternative for skills, cast rate and mana utility.',
        [
            "Cover resistances elsewhere before replacing Ancient's Pledge; compare Splendor "
            'and the complete defensive setup.',
            'Verify equip requirements; mana after kills requires credited kills.',
        ],
    ),
    ('druid', "Jalal's Mane"): (
        '+2 to Druid Skills, hit recovery and resistances support caster leveling.',
        [
            'Lore in an appropriate pelt or a strong rare pelt can provide more damage; '
            'compare actual skills and equip requirements.',
        ],
    ),
    **{
        (cls, name): (
            f"Death's Hand and Death's Guard support physical attacks before the level {respec} respec.",
            [
                'Wear both pieces for 30% increased attack speed and 15% all resistances; '
                'these are conditional pair bonuses.',
                "Cannot Be Frozen belongs to Death's Guard belt itself.",
                'After the caster respec, reassess the complete setup rather than inheriting the melee recommendation.',
                'Verify equip requirements and compare the complete defensive setup.',
            ],
        )
        for cls, respec in EARLY_MELEE_RESPECS.items()
        for name in ("Death's Hand", "Death's Guard")
    },
    **{
        (cls, 'Bloodfist'): (
            'Life and hit recovery support the entire leveling process, including after the caster respec.',
            [
                'The 10% increased attack speed benefits physical attacks, not casting; '
                '40 life and 30% hit recovery remain useful.',
                'Compare equip requirements, cast-rate alternatives and the complete defensive setup.',
            ],
        )
        for cls in EARLY_MELEE_RESPECS
    },
    ('assassin', 'Raven Frost'): (
        'Alternative source of Cannot Be Frozen for Assassin leveling from level 45.',
        ['Compare the full setup before replacing another Cannot Be Frozen source; verify equip requirements.'],
    ),
    ('assassin', "Mara's Kaleidoscope"): (
        'Later unique amulet option for skill-based Assassin leveling.',
        ['Compare class-skill or Trap-skill amulets and The Eye of Etlich; verify the higher equip requirements.'],
    ),
    ('assassin', 'The Stone of Jordan'): (
        'All skills support skill damage for the leveling Assassin.',
        ['Use if already available; compare the complete damage, mana and defensive setup.'],
    ),
    ('assassin', 'The Eye of Etlich'): (
        'Unique amulet alternative for skill-based Assassin leveling.',
        ['Compare against Assassin-skill or Trap-skill amulets and verify equip requirements.'],
    ),
    ('assassin', 'Skin of the Vipermagi'): (
        'All skills and resistances support Assassin leveling.',
        ['Compare the complete skill and resistance setup before replacing existing armor.'],
    ),
    ('assassin', 'Magefist'): (
        'Fire-skill gloves for Assassin leveling with Fire Traps and Death Sentry.',
        [
            'The fire-skill bonus does not increase Lightning Sentry; compare the skills actually used.',
            'Compare the complete attack-speed setup for trap placement.',
        ],
    ),
    **{
        ('assassin', name): (
            "Death's Hand and Death's Guard together support Assassin leveling.",
            [
                'The pair supplies 30% increased attack speed and 15% all resistances; '
                'these are conditional set bonuses, not standalone piece bonuses.',
                "Cannot Be Frozen belongs to Death's Guard belt itself.",
                "The guide recommends Ancient's Pledge alongside the pair for additional resistances.",
                'Verify the complete setup and equip requirements before replacing existing gear.',
            ],
        )
        for name in ("Death's Hand", "Death's Guard")
    },
    ('assassin', 'Twitchthroe'): (
        'Attack speed, hit recovery and increased blocking support the leveling Assassin.',
        ['Compare the complete attack-speed and recovery setup; blocking benefit requires a shield.'],
    ),
    ('druid', 'Spectral Shard'): (
        'Caster weapon alternative to Spirit Crystal Sword for leveling.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'Account for the dexterity investment when meeting weapon requirements.',
        ],
    ),
    ('druid', 'Suicide Branch'): (
        'Caster weapon alternative to Spirit Crystal Sword for leveling.',
        ['Compare the complete cast-rate breakpoint, skills, mana and defensive setup.'],
    ),
    ('druid', 'Skin of the Vipermagi'): (
        'Preferred caster leveling armor for cast rate, skills and resistances.',
        ['Compare the complete cast-rate breakpoint, skills, mana and defensive setup.'],
    ),
    ('druid', 'Magefist'): (
        'Cast-rate gloves for caster leveling; skill benefit depends on the spell used.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'The fire-skill bonus helps Fissure, not Tornado; cast-rate benefit depends on the total breakpoint.',
        ],
    ),
    ('paladin', 'Spectral Shard'): (
        'Caster weapon alternative to Spirit Crystal Sword for leveling.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'The cited guide recommendation is in the after level 18 respec setup.',
            'Account for the dexterity investment when meeting weapon requirements.',
        ],
    ),
    ('paladin', 'Suicide Branch'): (
        'Caster weapon alternative to Spirit Crystal Sword for leveling.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'The cited guide recommendation is in the after level 18 respec setup.',
        ],
    ),
    ('paladin', 'Skin of the Vipermagi'): (
        'Preferred caster leveling armor for cast rate, skills and resistances.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'The cited guide recommendation is in the after level 18 respec setup.',
        ],
    ),
    ('paladin', 'Magefist'): (
        'Cast-rate gloves for caster leveling; skill benefit depends on the spell used.',
        [
            'Compare the complete cast-rate breakpoint, skills, mana and defensive setup.',
            'The cited guide recommendation is in the after level 18 respec setup.',
            'The fire-skill bonus does not increase Blessed Hammer; cast-rate benefit depends on the total breakpoint.',
        ],
    ),
    **{
        (cls, name): (
            'Standalone movement speed makes these boots useful for leveling; no companion set piece is needed.',
            BOOT_GUIDE_CONDITIONS.get(cls, ()),
        )
        for cls in CLASSES
        for name in MOVEMENT_BOOTS
    },
    **{
        ('amazon', name): (
            'Optional Cow King set component for Amazon leveling.',
            [
                "Use Cow King's Hooves, Cow King's Hide and Cow King's Horns together with "
                "Death's Hand and Death's Guard; the guide pairs these with Ancient's Pledge.",
                'The attack-speed/resistance combination is not a bonus from a single piece; '
                'verify the complete setup and equip requirements.',
            ],
        )
        for name in COW_KING_PIECES
    },
    ('amazon', "Titan's Revenge"): (
        'Preferred javelin weapon for the leveling Amazon once equip requirements are met.',
        [
            'Meeting dexterity requirements early can cost vitality; compare the full attribute allocation.',
            'Replace attack speed lost from the previous weapon with other gear where needed.',
        ],
    ),
    ('amazon', 'Twitchthroe'): (
        'Attack speed, hit recovery and increased blocking support the leveling Amazon.',
        ['Compare the complete attack-speed and recovery setup; blocking benefit requires a shield.'],
    ),
}
PRIORITY = {
    'Magefist': 1,
    'Maelstrom': 1,
    'Tarnhelm': 1,
    'The Eye of Etlich': 1,
    'Bloodfist': 1,
    "Sander's Riprap": 1,
    'Skin of the Vipermagi': 1,
    'Pelta Lunata': 2,
    "Biggin's Bonnet": 2,
    'Nightsmoke': 2,
    'Infernal Cranium': 2,
    'Treads of Cthon': 2,
    'Nagelring': 5,
    "Sander's Paragon": 5,
}


def _key(name):
    return name.casefold().replace('\u2019', "'").strip()


def build_recommendations(candidates, facts, utility):
    """Build reviewed records; unreviewed evidence cannot become recommendations."""
    identities = {}
    for fact in facts['rows']:
        for name in [fact['name'], *fact.get('aliases', [])]:
            identities.setdefault(_key(name), {})[fact['item_id']] = fact
    rows, census = [], []
    for candidate in candidates['items']:
        name = candidate['name']
        record = {'name': name, 'source_locator': candidate['source_timestamp']}
        matches = identities.get(_key(name), {})
        reason = GENERAL.get(name) or CASTER.get(name) or MELEE.get(name)
        classes = list(CLASSES)
        archetypes = ['caster' if name in CASTER else 'melee' if name in MELEE else 'general']
        if name in RESTRICTED:
            cls, archetype, reason = RESTRICTED[name]
            classes, archetypes = [cls], [archetype]
        if name in GAPS or not reason or len(matches) != 1:
            record.update(
                status='gap',
                reason=GAPS.get(name)
                or (
                    'Runeword/base-dependent facts are not published in this recommendation layer.'
                    if candidate.get('item_kind') == 'runeword'
                    else 'Missing or ambiguous verified identity.'
                    if len(matches) != 1
                    else 'No reviewed applicability rule.'
                ),
            )
            census.append(record)
            continue
        fact = next(iter(matches.values()))
        conditions = CONDITIONS.get(name, []).copy()
        entry = {
            'id': 'leveling:' + fact['item_id'],
            'item_id': fact['item_id'],
            'name': fact['name'],
            'kind': 'recommendation',
            'intent': 'recommend',
            'purpose': 'leveling',
            'classes': classes,
            'archetypes': archetypes,
            'priority': PRIORITY.get(name, 3),
            'side': 'player',
            'stage': 'leveling',
            'reason': reason,
            'conditions': conditions,
            'benefits': [reason],
            'evidence_strength': 'explicit' if name in RESTRICTED else 'reviewed_inference',
            'source_id': 'mrllamasc-transcript',
            'source_locator': candidate['source_timestamp'],
            'source_date': '2025-04-24',
            'provenance': [{'source_id': 'mrllamasc-transcript', 'locator': candidate['source_timestamp']}],
            'review': (
                f'{TRANSCRIPT_REVIEW_DATES.get(name, "2026-09-23")}: applicability reviewed; '
                'general utility extended across classes, including Warlock. '
                'Historical source does not establish RotW-specific mechanics.'
            ),
        }
        rows.append(entry)
        if name in {'Rockstopper', "Duriel's Shell", 'Duskdeep'}:
            rows.append(
                {
                    **entry,
                    'id': entry['id'] + ':merc',
                    'side': 'merc',
                    'evidence_strength': 'explicit',
                    'conditions': [*conditions, 'Check mercenary level, strength and equipment-slot compatibility.'],
                }
            )
        census.append({**record, 'status': 'conditional' if conditions else 'accepted', 'item_id': fact['item_id']})
    guide_census = []
    source_ids = {'mrllamasc-transcript'}
    reviewed_rows = {(r.get('source_id'), r.get('source_locator'), r['name']): r for r in utility['rows']}
    for cls, name, locator in GUIDE_REVIEW:
        source_id = 'leveling-' + cls
        entry = next((r for r in rows if r['name'] == name and r['side'] == 'player'), None)
        benefit = GUIDE_BENEFITS.get((cls, name))
        matches = identities.get(_key(name), {})
        if benefit and len(matches) == 1:
            fact = next(iter(matches.values()))
            reason, conditions = benefit
            entry = {
                'id': 'leveling:' + fact['item_id'],
                'item_id': fact['item_id'],
                'name': fact['name'],
                'kind': 'recommendation',
                'intent': 'recommend',
                'purpose': 'leveling',
                'archetypes': list(GUIDE_ARCHETYPES.get((cls, name), ('general',))),
                'priority': GUIDE_PRIORITY.get((cls, name), 1),
                'side': 'player',
                'stage': 'leveling',
                'reason': reason,
                'conditions': list(conditions),
                'benefits': [reason],
            }
        snapshots = [s for s in utility['sources'] if s['id'] == source_id]
        source_verified = (
            len(snapshots) == 1
            and snapshots[0].get('sha256') == GUIDE_SOURCE_SHA256.get(source_id)
            and source_id in GUIDE_SOURCE_SHA256
        )
        source_name = GUIDE_SOURCE_NAMES.get((cls, name, locator), name)
        present = (source_id, locator, source_name) in reviewed_rows and source_verified
        guide_census.append(
            {
                'class': cls,
                'name': name,
                'source_id': source_id,
                'source_locator': locator,
                **({'source_label': source_name} if source_name != name else {}),
                'status': 'accepted' if present and entry else 'gap',
                **({} if source_verified else {'reason': 'Missing, ambiguous or changed reviewed source snapshot.'}),
            }
        )
        if not present or entry is None:
            continue
        source_ids.add(source_id)
        source_meta = snapshots[0]
        rows.append(
            {
                **entry,
                'id': entry['id'] + ':' + cls,
                'classes': [cls],
                'evidence_strength': 'explicit',
                'source_id': source_id,
                'source_locator': locator,
                'source_date': source_meta.get('source_date'),
                **({'source_label': source_name} if source_name != name else {}),
                'provenance': [{'source_id': source_id, 'locator': locator}],
                'review': (
                    GUIDE_REVIEW_DATES.get((cls, name), '2026-09-25' if cls == 'amazon' or benefit else '2026-09-23')
                    + ': reviewed explicit optional leveling equipment advice in the cited guide section.'
                ),
            }
        )
    for cls in ('sorceress', 'necromancer', 'warlock'):
        guide_census.append(
            {
                'class': cls,
                'name': 'Ring / Amulet vendor mentions',
                'source_id': 'leveling-' + cls,
                'source_locator': 'playstyle-progression-header',
                'status': 'excluded',
                'reason': 'Pickup-to-sell instructions are not equipment advice.',
            }
        )
    patterns = [
        {
            **p,
            'item_id': None,
            'kind': 'recommendation_pattern',
            'status': 'conditional',
            'intent': 'pattern',
            'source_id': 'mrllamasc-transcript',
            'reason': 'Requires matching the actual item and verifying its requirements.',
        }
        for p in candidates['generic_patterns']
    ]
    exclusions = [{**p, 'status': 'excluded', 'intent': 'exclude'} for p in candidates['negative_or_scope_mentions']]
    source = next(
        (s for s in utility['sources'] if s['id'] == 'mrllamasc-transcript'),
        {
            'id': 'mrllamasc-transcript',
            'path': candidates.get('transcript_path'),
            'sha256': candidates.get('transcript_sha256'),
            'source_date': '2025-04-24',
        },
    )
    class_coverage = {}
    for cls in CLASSES:
        mentions = sum(r.get('class') == cls for r in utility['rows'])
        class_coverage[cls] = {
            'recommendations': sum(cls in r['classes'] for r in rows),
            'cached_evidence_rows': mentions,
            'gap': (
                'Class guide and shared-planner evidence is not automatically advice; '
                'build-specific and mercenary review remains incomplete.'
            ),
        }
    return {
        'schema_version': 1,
        'generated_at': '2026-09-23',
        'adapter_version': 1,
        'sources': [source, *[s for s in utility['sources'] if s['id'] in source_ids - {'mrllamasc-transcript'}]],
        'rows': rows,
        'patterns': patterns,
        'coverage': {
            'named': census,
            'guide_reviews': guide_census,
            'patterns': len(patterns),
            'exclusions': exclusions,
            'classes': class_coverage,
            'gaps': [
                'Named unique/set recommendations are reviewed, not an exhaustive leveling list.',
                'Runeword/base eligibility remains in existing socket and utility evidence.',
                'Mercenary coverage is limited to three reviewed defensive helm/body options.',
                'Pre-RotW transcript class-independent utility is reviewed inference for Warlock.',
            ],
        },
    }


def export_recommendations(root):
    paths = {
        key: root / 'pricing/data' / filename
        for key, filename in {
            'candidates': 'appraisal-leveling-candidates-2026-09-23.json',
            'facts': 'appraisal-item-facts.json',
            'utility': 'appraisal-utility.json',
        }.items()
    }
    payload = build_recommendations(**{key: json.loads(path.read_text()) for key, path in paths.items()})
    payload['inputs'] = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()
    }
    output = root / 'pricing/data/appraisal-recommendations.json'
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    return payload


if __name__ == '__main__':
    result = export_recommendations(Path(__file__).resolve().parents[2])
    print(json.dumps({'recommendations': len(result['rows']), 'coverage': result['coverage']}))
