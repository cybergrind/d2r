"""Explicitly reviewed player utility families, compiled only during maintenance."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Crown of Ages': {
        'slots': ('Helmets',),
        'role': 'Caster resistance and physical damage reduction helmet',
        'important_stats': ('127:0', '99:0', '39:0', '41:0', '43:0', '45:0', '36:0', '31:0', '16:0'),
        'desirable': ('127:0', '99:0', '36:0', '39:0', '41:0', '43:0', '45:0'),
        'allowed_sockets': (1, 2),
        'conditions': (
            'One socket and native minimum resistance/damage reduction remain usable; two sockets are a better '
            'socket-capacity roll, not proof of any inserted jewels or runes. Check the high equipment requirements '
            'and retain needed Faster Cast Rate elsewhere.',
            'Physical damage reduction, resistance and recovery caps depend on the full loadout. '
            'Native indestructibility does not create a naturally ethereal version.',
        ),
    },
    'Stormshield': {
        'slots': ('Off-Hand',),
        'role': 'Caster physical damage reduction and blocking shield',
        'important_stats': ('36:0', '0:0', '102:0', '41:0', '20:0', '43:0', '214:0'),
        'desirable': ('36:0', '102:0', '20:0', '41:0', '43:0'),
        'allowed_sockets': (0, 1),
        'conditions': (
            'Block chance depends on class, level and Dexterity; the shield alone does not establish maximum block. '
            'Meet its requirements and preserve needed Faster Cast Rate elsewhere.',
            'Defense scales with character level. Lightning thorns are not caster spell damage, and no socket filler '
            'is assumed. Native indestructibility does not create a naturally ethereal version.',
        ),
    },
    'Leviathan': {
        'classes': ('Paladin',),
        'slots': ('Body Armors',),
        'role': 'Zeal physical damage reduction armor alternative',
        'important_stats': ('36:0', '0:0', '16:0', '31:0'),
        'desirable': ('36:0', '0:0'),
        'conditions': (
            'Physical damage reduction is capped across the setup; it does not reduce '
            'elemental damage. Native indestructibility prevents normal ethereal '
            'spawning. Check equip requirements before relying on its Strength; no '
            'socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Steelrend': {
        'classes': ('Paladin',),
        'slots': ('Gloves',),
        'role': 'Zeal off-weapon damage and Crushing Blow gloves alternative',
        'important_stats': ('17:0', '18:0', '136:0', '0:0', '31:0'),
        'desirable': ('17:0', '18:0', '136:0'),
        'conditions': (
            'Enhanced Damage on gloves is off-weapon physical damage, not weapon ED '
            'or spell damage. Crushing Blow is target-dependent; these gloves have no '
            'IAS. Check the full attack-speed breakpoint and Strength requirement.',
        ),
    },
    "Magnus' Skin": {
        'classes': ('Paladin',),
        'slots': ('Gloves',),
        'role': 'Zeal attack speed and accuracy gloves alternative',
        'important_stats': ('93:0', '19:0', '39:0', '16:0'),
        'desirable': ('93:0', '19:0'),
        'conditions': (
            'Standalone attack speed, attack rating, fire resistance and defense; '
            'no Orphan set companions or full-set bonus are assumed. Attack Rating '
            'does not guarantee a hit.',
        ),
        'quality': 'set',
    },
    "Razor's Edge": {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Zeal Deadly Strike and Open Wounds weapon alternative',
        'important_stats': ('17:0', '18:0', '93:0', '116:0', '141:0', '135:0'),
        'desirable': ('17:0', '18:0', '93:0', '141:0', '135:0'),
        'conditions': (
            'Target defense reduction is not Ignore Target Defense and has '
            'target-specific effectiveness. Deadly Strike and critical effects do '
            'not multiply into quadruple damage. Ethereal melee use requires '
            'observed Indestructible; no socket filler is presumed.',
        ),
        'allow_indestructible': True,
        'allowed_sockets': (0, 1),
    },
    'Alma Negra': {
        'classes': ('Paladin',),
        'slots': ('Off-Hand',),
        'role': 'Zeal skill, block and off-weapon damage shield alternative',
        'important_stats': ('83:3', '102:0', '20:0', '35:0', '119:0', '17:0', '18:0', '16:0'),
        'desirable': ('83:3', '102:0', '20:0', '17:0', '18:0', '119:0'),
        'conditions': (
            'Shield Enhanced Damage is off-weapon physical damage. Block chance '
            'still needs character level and Dexterity; no maximum block or '
            'elemental resistance is inferred. No socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Buriza-Do Kyanon': {
        'classes': ('Amazon',),
        'slots': ('Weapon',),
        'role': 'Strafe piercing crossbow alternative',
        'important_stats': ('156:0', '93:0', '17:0', '18:0', '218:0', '2:0', '54:0', '55:0', '134:0'),
        'desirable': ('156:0', '93:0', '17:0', '18:0', '218:0'),
        'conditions': (
            'Native Ballista or upgraded Colossus Crossbow are permitted. '
            'Piercing does not exceed its useful chance cap; Strafe speed '
            'depends on crossbow breakpoints. Cold damage and freeze can '
            'change corpse availability; bows/crossbows do not have normal '
            'ethereal variants. No socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Bloodpact Shard': {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Echoing Strike cast speed and demon utility dagger alternative',
        'important_stats': ('127:0', '105:0', '76:0', '107:378', '107:380', '107:382', '80:0'),
        'desirable': ('127:0', '105:0', '76:0'),
        'conditions': (
            'Blood Oath, Blood Boil and Bind Demon support the appropriate '
            'demon setup, not hard-point synergies. Slows Target is not applied '
            'by Echoing Strike. This casting-only role does not establish safe '
            'melee durability or an attack weapon damage premium.',
        ),
        'casting_only': True,
        'allowed_sockets': (0, 1),
    },
    'Earthshaker': {
        'classes': ('Druid',),
        'slots': ('Weapon',),
        'role': 'Fissure elemental skill weapon alternative',
        'important_stats': ('188:42',),
        'desirable': ('188:42',),
        'conditions': (
            'Elemental skill levels support Fissure. Weapon Enhanced Damage, IAS, '
            'knockback and the on-striking Fissure proc do not improve a cast '
            'Fissure. Ethereal is accepted for casting only; no melee durability or '
            'socket filler is assumed.',
        ),
        'casting_only': True,
        'allowed_sockets': (0, 1),
    },
    'Measured Wrath': {
        'classes': ('Warlock',),
        'slots': ('Off-Hand',),
        'role': 'Fire Warlock casting and fire skill book alternative',
        'important_stats': (
            '83:7',
            '105:0',
            '107:394',
            '107:398',
            '107:376',
            '3:0',
            '86:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '16:0',
        ),
        'desirable': ('83:7', '105:0', '107:394', '107:398', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Ring of Fire and Flame Wave skill levels support fire casting, not '
            'hard-point synergies. Summon Tainted is demon utility. The '
            'when-struck Ring of Fire proc is not a guaranteed defensive or '
            'damage effect. No socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'The Rising Sun': {
        'classes': ('Warlock',),
        'slots': ('Amulets',),
        'role': 'Fire skill and level-scaled fire absorption amulet alternative',
        'important_stats': ('126:1', '235:0', '74:0'),
        'desirable': ('126:1', '235:0'),
        'conditions': (
            'Fire skill levels support eligible fire skills. Level-scaled flat '
            'fire absorption is not percentage absorption or immunity and '
            'requires the character level. Added weapon fire damage and the '
            'when-struck Meteor proc do not increase normal spell damage.',
        ),
        'allowed_sockets': (0,),
    },
    "Horazon's Countenance": {
        'classes': ('Warlock',),
        'slots': ('Helmets',),
        'role': 'Fire Warlock class skill helm alternative',
        'important_stats': ('83:7', '0:0', '35:0'),
        'desirable': ('83:7', '35:0'),
        'conditions': (
            'Standalone Warlock skill, Strength and magic damage '
            'reduction only. Attack Rating does not improve fire spell '
            'accuracy. Conditional maximum life and extra Strength '
            'require additional set pieces; no full-set bonuses or socket '
            'filler are assumed.',
        ),
        'quality': 'set',
        'allowed_sockets': (0, 1),
    },
    "Horazon's Dominion": {
        'classes': ('Warlock',),
        'slots': ('Body Armors',),
        'role': 'Fire Warlock mana and resistance armor alternative',
        'important_stats': ('9:0', '43:0', '39:0', '41:0', '16:0'),
        'desirable': ('9:0', '43:0', '39:0', '41:0'),
        'conditions': (
            'Demons skill levels are not Chaos fire skill levels. Standalone '
            'mana, fire/cold/lightning resistance and defense are evaluated; '
            'conditional poison resistance, Vitality and damage reduction '
            'require companion pieces.',
        ),
        'quality': 'set',
        'allowed_sockets': (0, 1),
    },
    "Horazon's Legacy": {
        'classes': ('Warlock',),
        'slots': ('Boots',),
        'role': 'Fire Warlock movement and magic resistance boots alternative',
        'important_stats': ('96:0', '0:0', '2:0', '37:0', '153:0'),
        'desirable': ('96:0', '37:0', '153:0'),
        'conditions': (
            'Magic resistance is distinct from magic damage reduction or '
            'elemental resistance. Cannot Be Frozen does not prevent every '
            'slow. Extra set movement requires another piece; the standalone '
            'movement value is not a full-set bonus.',
        ),
        'quality': 'set',
    },
    "Arioc's Needle": {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Echoing Strike skill and physical damage spear alternative',
        'important_stats': ('127:0', '17:0', '18:0', '141:0', '115:0'),
        'desirable': ('127:0', '17:0', '18:0', '141:0'),
        'conditions': (
            "Echoing Strike uses FCR, not this spear's IAS. Weapon damage and "
            'Deadly Strike support the physical echoes. Ignore Target Defense '
            'does not cover every boss or unique target. This casting-only '
            'alternative does not imply melee durability safety; check the '
            'actual two-handed weapon/off-hand combination. No socket filler is '
            'assumed.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    "Tyrael's Might": {
        'classes': ('Amazon',),
        'slots': ('Body Armor',),
        'role': 'Strafe resistance and Cannot Be Frozen armor alternative',
        'important_stats': ('153:0', '96:0', '39:0', '41:0', '43:0', '45:0', '0:0', '121:0', '16:0'),
        'desirable': ('153:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Damage to Demons applies against demon targets; it is not a '
            'universal damage multiplier. Cannot Be Frozen does not prevent '
            'every slow. Requirements -100% does not remove the level '
            'requirement. Rest in Peace changes corpse availability. The native '
            'indestructible unique does not have a normal ethereal drop variant; '
            'no socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Shadow Dancer': {
        'classes': ('Assassin',),
        'slots': ('Boots',),
        'role': 'Dragon Talon kick base and recovery boots alternative',
        'important_stats': ('188:49', '99:0', '96:0', '2:0', '16:0'),
        'desirable': ('188:49', '99:0', '2:0'),
        'conditions': (
            'Myrmidon Greaves supply the kick base; Enhanced Defense and ethereal '
            'defense do not increase kick damage. Shadow Disciplines support the '
            'relevant utility skills, not Martial Arts levels or hard-point '
            'synergies. Check the actual strength/level requirement and full '
            'attack-speed setup; these boots have no IAS.',
        ),
    },
    "Atma's Scarab": {
        'classes': ('Amazon', 'Barbarian'),
        'slots': ('Amulets',),
        'role': 'Physical attack Amplify Damage amulet alternative',
        'important_stats': ('198:4226', '119:0', '45:0'),
        'desirable': ('198:4226', '119:0'),
        'conditions': (
            'Amplify Damage requires an eligible on-striking proc and can be '
            'overwritten by other curses. It supports physical attack damage; it '
            'is not automatically active and does not boost unrelated elemental '
            'damage. Attack Rating remains target-dependent.',
        ),
        'allowed_sockets': (0,),
    },
    "Astreon's Iron Ward": {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Blessed Hammer combat skill scepter alternative',
        'important_stats': ('188:24', '34:0'),
        'desirable': ('188:24',),
        'conditions': (
            'Paladin Combat skills support Blessed Hammer; weapon Enhanced '
            'Damage, flat weapon Damage, IAS, Crushing Blow and Attack '
            'Rating do not multiply Hammer spell damage. Flat damage '
            'reduction is a separate survival benefit. No staffmods or '
            'socket filler is assumed; casting does not consume weapon '
            'durability.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    'Azurewrath': {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Dream Paladin elemental attack sword alternative',
        'important_stats': (
            '127:0',
            '93:0',
            '151:119',
            '17:0',
            '18:0',
            '52:0',
            '53:0',
            '54:0',
            '55:0',
            '0:0',
            '1:0',
            '2:0',
            '3:0',
        ),
        'desirable': ('127:0', '93:0', '151:119'),
        'conditions': (
            'Sanctuary is an equipped aura with undead-specific effects, not a '
            'general resistance reduction for Holy Shock. Added elemental attack '
            'damage and weapon Enhanced Damage are separate from Holy Shock '
            'lightning damage. Check the full Zeal speed setup and no socket filler '
            'is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Lightsabre': {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Dream Paladin attack speed and lightning absorb sword alternative',
        'important_stats': ('93:0', '144:0', '62:0', '17:0', '18:0', '115:0'),
        'desirable': ('93:0', '144:0'),
        'conditions': (
            'Lightning Absorb is percentage absorption and capped in the full setup. '
            'Weapon Enhanced Damage does not multiply Holy Shock lightning damage; '
            'mana leech needs physical damage and a drainable target. Ignore Target '
            'Defense does not cover every boss or unique target. No socket filler is '
            'assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Fleshripper': {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Smite Crushing Blow and Open Wounds dagger alternative',
        'important_stats': ('136:0', '135:0', '150:0'),
        'desirable': ('136:0', '135:0'),
        'conditions': (
            'Crushing Blow and Open Wounds support Smite. Weapon Enhanced Damage, '
            'Deadly Strike and target defense reduction do not improve Smite damage '
            'or hit chance. Slows Target has target-specific limits; do not infer '
            'an Uber healing counter from Prevent Monster Heal. Ethereal melee use '
            'needs observed Indestructible, such as an inserted Zod, using the only '
            'socket.',
        ),
        'allowed_sockets': (0, 1),
        'allow_indestructible': True,
    },
    "Death's Web": {
        'classes': ('Necromancer',),
        'slots': ('Weapon',),
        'role': 'Poison Nova skills and resistance piercing wand',
        'important_stats': ('127:0', '188:17', '336:0', '86:0', '138:0'),
        'desirable': ('127:0', '188:17', '336:0'),
        'conditions': (
            'Poison skills and enemy poison resistance reduction support Poison '
            'Nova. Resistance reduction alone does not break immunity. Life and '
            'mana after each kill require wearer kill credit; casting does not '
            'consume weapon durability. No socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    "Mang Song's Lesson": {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Warlock casting staff alternative',
        'important_stats': ('127:0', '105:0', '27:0'),
        'desirable': ('127:0', '105:0'),
        'conditions': (
            'All Skills and casting speed support Warlock skill use. '
            'Elemental resistance piercing does not increase physical or '
            'magic damage; only the Fire build receives a fire-piercing '
            'priority. Two-handed staff use must satisfy the actual '
            'weapon/shield rules. No socket filler is assumed. Casting-only '
            'use does not authorize melee durability safety.',
        ),
        'allowed_sockets': (0, 1),
        'build_stats': {'fire-warlock-guide': {'class': 'Warlock', 'keys': ('333:0',)}},
        'casting_only': True,
    },
    "Ondal's Wisdom": {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Warlock casting and experience staff alternative',
        'important_stats': ('127:0', '105:0', '1:0', '31:0', '85:0', '35:0'),
        'desirable': ('127:0', '105:0'),
        'conditions': (
            'All Skills and casting speed support skill use. Experience gain '
            'requires the staff to be active and does not multiply damage or '
            'Magic Find. Flat defense and magic damage reduction are separate. '
            'No socket filler is assumed. Casting-only use does not authorize '
            'melee durability safety.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    'Razorswitch': {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Warlock skill and survival staff alternative',
        'important_stats': ('127:0', '105:0', '9:0', '7:0', '35:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'This alternative supplies casting speed, skills and survival, not '
            'Enhanced Damage. Attacker Takes Damage is not a spell damage '
            'multiplier. Compare the complete weapon/shield setup and equip '
            'requirements; no socket filler is assumed. Casting-only use does not '
            'authorize melee durability safety.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    'Skull Collector': {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'role': 'Echoing Strike skill and Magic Find staff alternative',
        'important_stats': ('127:0', '77:0', '138:0', '240:0'),
        'desirable': ('127:0', '240:0'),
        'conditions': (
            'Magic Find scales with character level and must be active when the '
            'reward is generated. Mana after each kill needs wearer kill '
            'credit. This staff has no FCR or Enhanced Damage; compare the '
            'weapon damage and casting-speed tradeoff. No socket filler is '
            'assumed. Casting-only use does not authorize melee durability '
            'safety.',
        ),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    "Ars Al'Diabolos": {
        'classes': ('Warlock',),
        'slots': ('Off-Hand',),
        'role': 'Fire Warlock skill and fire damage grimoire',
        'important_stats': ('188:58', '105:0', '329:0', '138:0', '39:0', '107:401', '16:0'),
        'desirable': ('188:58', '105:0', '329:0', '107:401'),
        'conditions': (
            'Chaos skills, Apocalypse levels and Fire Skill Damage support fire '
            'spells. Item skill bonuses do not supply hard-point synergies. '
            'Terror requires a when-struck proc and is not assumed active. No '
            'extra staffmods or socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    "Ars Dul'Mephistos": {
        'classes': ('Warlock',),
        'slots': ('Off-Hand',),
        'role': 'Fire Warlock casting and recovery grimoire alternative',
        'important_stats': ('83:7', '105:0', '99:0', '16:0', '80:0'),
        'desirable': ('83:7', '105:0', '99:0'),
        'conditions': (
            'Warlock skills and casting speed help the fire build. Enhanced '
            'Damage, Attack Rating and magic resistance piercing do not '
            'multiply its fire spells. Blizzard requires a when-struck proc; '
            'no permanent cold damage or socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    "Ars Tor'Baalos": {
        'classes': ('Warlock',),
        'slots': ('Off-Hand',),
        'role': 'Fire Warlock demon utility and survival grimoire alternative',
        'important_stats': ('188:56', '107:374', '107:380', '107:379', '107:381', '16:0', '216:0', '36:0'),
        'desirable': ('36:0', '216:0'),
        'conditions': (
            'Demon utility skill bonuses require using those skills and an '
            'appropriate demon setup; they do not directly raise Chaos fire '
            'skill levels. Item bonuses do not grant hard-point synergies. Life '
            'scales with character level; Decrepify needs a when-struck proc. No '
            'socket filler is assumed.',
        ),
        'allowed_sockets': (0, 1),
    },
    'Entropy Locket': {
        'classes': ('Warlock', 'Sorceress'),
        'slots': ('Amulets',),
        'role': 'Casting and mana amulet alternative',
        'important_stats': ('105:0', '41:0', '77:0', '35:0'),
        'desirable': ('105:0', '77:0'),
        'conditions': (
            'Casting speed, mana and survival support the listed builds. Magic '
            'Skill Damage supports the Echoing Strike build through active Hex: '
            'Purge magic damage, not the physical echoes themselves; it does not '
            'multiply Nova lightning damage. Miasma Chains requires an '
            'on-striking event, which Echoing Strike cannot trigger. No '
            'additional skill levels are supplied.',
        ),
        'allowed_sockets': (0,),
        'build_stats': {'echoing-strike-warlock-guide': {'class': 'Warlock', 'keys': ('357:0',)}},
    },
    'Sling': {
        'classes': ('Paladin',),
        'slots': ('Rings',),
        'role': 'Blessed Hammer casting and magic piercing ring',
        'important_stats': ('105:0', '358:0', '1:0', '80:0'),
        'desirable': ('105:0', '358:0'),
        'conditions': (
            'Magic resistance piercing supports Blessed Hammer but does not itself break '
            'immunity. Slows Target does not apply through Hammer casts. Town Portal is '
            'an active utility oskill, not a combat skill level or damage bonus.',
        ),
    },
    "Gheed's Wager": {
        'classes': ('Paladin', 'Warlock'),
        'slots': ('Belts',),
        'role': 'Casting, recovery and resistance belt alternative',
        'important_stats': ('105:0', '99:0', '96:0', '16:0', '39:0', '41:0', '43:0', '45:0', '79:0'),
        'desirable': ('105:0', '99:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Casting and survival bonuses support both listed builds. Magic '
            'piercing supports Blessed Hammer, not the Fire Warlock fire spells. '
            'Gold Find must be active for rewards; it does not increase Magic '
            'Find.',
        ),
        'build_stats': {'blessed-hammer-paladin': {'class': 'Paladin', 'keys': ('358:0',)}},
    },
    'Wraithstep': {
        'classes': ('Warlock',),
        'slots': ('Boots',),
        'role': 'Fire Warlock skill-tab and recovery boots alternative',
        'important_stats': ('188:58', '96:0', '99:0', '31:0', '2:0', '1:0'),
        'desirable': ('188:58', '96:0', '99:0'),
        'conditions': (
            'The random Warlock skill tab matters: prioritize Chaos for this fire '
            'build, not an assumed matching tab on every copy. Movement, recovery '
            'and attributes are separate benefits. Skill bonuses do not grant '
            'hard-point synergies.',
        ),
    },
    'Opalvein': {
        'classes': ('Warlock',),
        'slots': ('Rings',),
        'role': 'Fire Warlock casting and resistance ring alternative',
        'important_stats': ('105:0', '39:0', '41:0', '43:0', '45:0', '86:0', '138:0', '329:0'),
        'desirable': ('105:0', '39:0', '41:0', '43:0', '45:0', '329:0'),
        'conditions': (
            'Casting and resistance support fire spells; life and mana after each kill '
            'require wearer kill credit. Flame Wave on attack is not triggered by '
            'every spell cast. Only an observed Fire Skill Damage modifier from the '
            'random property group boosts these fire spells; magic, physical, cold, '
            'lightning and poison alternatives do not.',
        ),
    },
    "Bartuc's Cut-Throat": {
        'slots': ('Weapon',),
        'role': 'Assassin trap skills and recovery claw alternative',
        'important_stats': ('83:6', '99:0', '0:0', '2:0'),
        'desirable': ('83:6', '99:0'),
        'conditions': (
            'Assassin skills support traps; Martial Arts levels, weapon '
            'Enhanced Damage, Attack Rating and life leech do not improve '
            'trap damage. Trap placement does not consume claw durability, '
            'but melee attacks do. Claw base speed and the full IAS setup '
            'govern trap placement; no socket filler is assumed.',
        ),
        'classes': ('Assassin',),
        'allowed_sockets': (0, 1),
        'casting_only': True,
    },
    'Windforce': {
        'slots': ('Weapon',),
        'role': 'Strafe physical damage bow',
        'important_stats': ('17:0', '18:0', '218:0', '93:0', '62:0', '81:0', '0:0', '2:0'),
        'desirable': ('17:0', '18:0', '218:0', '93:0'),
        'conditions': (
            'Maximum weapon damage scales with character level. Mana leech needs '
            'physical damage and target drain; Knockback provides spacing on eligible '
            'hits. Compare the full Strafe speed setup and do not assume a socket '
            'jewel.',
        ),
        'classes': ('Amazon',),
        'allowed_sockets': (0, 1),
    },
    'Eaglehorn': {
        'slots': ('Weapon',),
        'role': 'Strafe level-scaled damage bow alternative',
        'important_stats': ('17:0', '18:0', '219:0', '224:0', '83:0', '2:0', '115:0'),
        'desirable': ('17:0', '18:0', '219:0', '83:0'),
        'conditions': (
            'Maximum damage and Attack Rating scale with level. Ignore Target Defense '
            'does not cover every boss or unique target. This bow has no native IAS; '
            'check the complete attack-speed setup. No socket filler is assumed.',
        ),
        'classes': ('Amazon',),
        'allowed_sockets': (0, 1),
    },
    "M'avina's Caster": {
        'slots': ('Weapon',),
        'role': 'Strafe set bow alternative',
        'important_stats': ('17:0', '18:0', '93:0', '19:0'),
        'desirable': ('17:0', '18:0', '93:0'),
        'conditions': (
            'Native weapon damage and IAS support Strafe. Fires Magic Arrows '
            'applies to the normal attack, not as an automatic replacement for '
            'Strafe. Extra magic damage, Nova proc and Bow skills require '
            'companion set pieces and are not inferred from this bow alone.',
        ),
        'quality': 'set',
        'classes': ('Amazon',),
        'allowed_sockets': (0, 1),
    },
    'Widowmaker': {
        'slots': ('Weapon',),
        'role': 'Enchant delivery through Guided Arrow alternative',
        'important_stats': ('97:22',),
        'desirable': ('97:22',),
        'conditions': (
            'Guided Arrow is an oskill that must be selected and used. Enchant must '
            'be supplied separately; the bow does not grant it. Weapon Enhanced '
            'Damage and Deadly Strike do not multiply Enchant fire damage. The bow '
            'has no IAS; check attack speed and no socket filler is assumed.',
        ),
        'classes': ('Sorceress',),
        'allowed_sockets': (0, 1),
    },
    'Tomb Reaver': {
        'slots': ('Weapon',),
        'role': 'Warlock weapon damage and socket customization alternative',
        'important_stats': (
            '17:0',
            '18:0',
            '194:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '80:0',
            '86:0',
            '122:0',
            '124:0',
        ),
        'desirable': ('17:0', '18:0', '194:0'),
        'build_stats': {'mirrored-blades-warlock-guide': {'class': 'Warlock', 'keys': ('93:0',)}},
        'casting_only_builds': ('echoing-strike-warlock-guide',),
        'conditions': (
            'Prefer three native sockets for customization, but no Zod or IAS '
            'jewels are assumed. Echoing Strike uses FCR for its casts, not IAS; '
            'its casting-only alternative does not imply melee durability safety. '
            'Mirrored Blades uses IAS and weapon durability: ethereal melee use '
            'requires observed Indestructible, such as a socketed Zod, using '
            'customization space. Life after each kill requires wearer kill credit; '
            'reanimation is not a guaranteed active summon.',
        ),
        'classes': ('Warlock',),
        'allowed_sockets': (1, 2, 3),
        'allow_indestructible': True,
    },
    "Immortal King's Will": {
        'slots': ('Helmets',),
        'role': 'Warcries and Find helmet alternative',
        'important_stats': ('188:34', '79:0', '80:0'),
        'desirable': ('188:34', '79:0', '80:0'),
        'conditions': (
            'Warcries support buffs and Find Item. Two native sockets are '
            'available, but no gold or magic-find fillers or other set '
            'pieces are assumed.',
        ),
        'quality': 'set',
        'classes': ('Barbarian',),
        'allowed_sockets': (2,),
    },
    "Arreat's Face": {
        'slots': ('Helmets',),
        'role': 'Barbarian skills and survival helmet',
        'important_stats': ('83:4', '188:32', '99:0', '119:0', '0:0', '2:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('83:4', '188:32', '99:0'),
        'conditions': (
            'Combat skill levels support attacks; attack speed still '
            'depends on the full setup. Ordinary life leech does not heal '
            'Berserk magic damage. Compare equip requirements and do not '
            'assume a socket filler.',
        ),
        'classes': ('Barbarian',),
        'allowed_sockets': (0, 1),
        'build_stats': {'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ('60:0',)}},
    },
    "Nightwing's Veil": {
        'slots': ('Helmets',),
        'role': 'Cold spell damage helmet',
        'important_stats': ('127:0', '331:0', '2:0', '149:0', '118:0'),
        'desirable': ('127:0', '331:0'),
        'conditions': (
            'Cold skill damage supports Blizzard. Cold absorb is flat and '
            'Half Freeze Duration is not Cannot Be Frozen. Dexterity does '
            'not establish maximum block; no cold facet is assumed.',
        ),
        'classes': ('Sorceress',),
        'allowed_sockets': (0, 1),
    },
    'Ravenlore': {
        'slots': ('Helmets',),
        'role': 'Druid fire damage helmet',
        'important_stats': ('188:42', '333:0', '39:0', '41:0', '43:0', '45:0', '1:0'),
        'desirable': ('188:42', '333:0'),
        'conditions': (
            'Elemental skills and enemy fire resistance reduction support '
            'Fissure. Resistance reduction alone does not break fire '
            'immunity; Raven levels do not improve Fissure. No fire facet '
            'is assumed.',
        ),
        'classes': ('Druid',),
        'allowed_sockets': (0, 1),
    },
    'Valkyrie Wing': {
        'slots': ('Helmets',),
        'role': 'Amazon skill and mana sustain helmet',
        'important_stats': ('83:0', '96:0', '99:0', '138:0'),
        'desirable': ('83:0', '138:0'),
        'conditions': (
            'Amazon skills support Lightning Strike; movement and recovery '
            'depend on the full setup. Mana after each kill needs wearer '
            'kill credit and is distinct from mana leech.',
        ),
        'classes': ('Amazon',),
        'allowed_sockets': (0, 1),
    },
    'Giant Skull': {
        'slots': ('Helmets',),
        'role': 'Knockback and socket customization helmet',
        'important_stats': ('81:0', '136:0', '0:0', '194:0'),
        'desirable': ('81:0', '194:0'),
        'conditions': (
            'Prefer two native sockets for customization; no IAS or damage '
            'jewels are assumed. Knockback supplies spacing for eligible '
            'attacks and Crushing Blow has reduced effect on ranged '
            'attacks. Check the complete speed setup.',
        ),
        'allowed_sockets': (1, 2),
    },
    "Sander's Taboo": {
        'slots': ('Gloves',),
        'role': 'Attack speed and life gloves alternative',
        'important_stats': ('93:0', '7:0'),
        'desirable': ('93:0', '7:0'),
        'conditions': (
            'IAS supports javelin attacks, not casting. Native poison '
            'attack damage does not increase lightning spell damage; no '
            'other set pieces are assumed.',
        ),
        'quality': 'set',
        'classes': ('Amazon',),
    },
    'Nightsmoke': {
        'slots': ('Belts',),
        'role': 'Resistance and mana belt alternative',
        'important_stats': ('39:0', '41:0', '43:0', '45:0', '9:0', '114:0', '34:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0', '9:0'),
        'conditions': (
            'Damage Taken Goes to Mana returns mana from eligible damage '
            'to life; it does not absorb or reduce incoming damage. '
            'Upgrading changes belt capacity and equip requirements.',
        ),
    },
    'Credendum': {
        'slots': ('Belts',),
        'role': 'Attributes and resistance belt alternative',
        'important_stats': ('0:0', '2:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Standalone Strength, Dexterity and all resistance support '
            'equip requirements and survival. Other Disciple set bonuses '
            'require companion items and are not inferred.',
        ),
        'quality': 'set',
    },
    "Trang-Oul's Guise": {
        'slots': ('Helmets',),
        'role': 'Mana and recovery helmet alternative',
        'important_stats': ('99:0', '9:0', '74:0'),
        'desirable': ('99:0', '9:0'),
        'conditions': (
            'These are standalone mana and recovery benefits. Full-set '
            'transformation and bonuses are not inferred; check the '
            'complete recovery and casting setup.',
        ),
        'quality': 'set',
        'allowed_sockets': (0, 1),
    },
    "Trang-Oul's Scales": {
        'slots': ('Body Armor',),
        'role': 'Movement and summoning support armor alternative',
        'important_stats': ('188:18', '96:0', '45:0', '32:0'),
        'desirable': ('96:0', '45:0'),
        'conditions': (
            'Summoning skills support minions, not Poison Nova damage. '
            'Lightning resistance and physical damage reduction require '
            'companion set pieces; neither is a standalone armor '
            'property.',
        ),
        'quality': 'set',
        'classes': ('Necromancer',),
        'allowed_sockets': (0, 1),
    },
    "M'avina's True Sight": {
        'slots': ('Helmets',),
        'role': 'Attack speed set helmet alternative',
        'important_stats': ('93:0', '9:0', '74:0'),
        'desirable': ('93:0',),
        'conditions': (
            'Native IAS supports Strafe. All Skills, bonus Attack Rating '
            'and all resistance are conditional set bonuses; do not infer '
            'them or a socket jewel from this helmet alone.',
        ),
        'quality': 'set',
        'allowed_sockets': (0, 1),
    },
    "M'avina's Embrace": {
        'slots': ('Body Armor',),
        'role': 'Passive skills and magic reduction armor alternative',
        'important_stats': ('188:1', '35:0', '31:0'),
        'desirable': ('188:1', '35:0'),
        'conditions': (
            'Passive and Magic skills support Amazon passives. Faster Hit '
            'Recovery requires companion set pieces; the when-struck '
            'Glacial Spike is not a permanent effect. Magic Damage Reduced '
            'is flat.',
        ),
        'quality': 'set',
        'classes': ('Amazon',),
        'allowed_sockets': (0, 1),
    },
    "M'avina's Icy Clutch": {
        'slots': ('Gloves',),
        'role': 'Attributes and cold attack gloves alternative',
        'important_stats': ('0:0', '2:0', '118:0', '54:0', '55:0'),
        'desirable': ('0:0', '2:0'),
        'conditions': (
            'Standalone cold attack damage and attributes are separate '
            'from the much larger conditional cold damage and cold skill '
            'damage bonuses. Those require companion pieces. Half Freeze '
            'Duration is not Cannot Be Frozen.',
        ),
        'quality': 'set',
    },
    "M'avina's Tenet": {
        'slots': ('Belts',),
        'role': 'Movement and mana-leech belt alternative',
        'important_stats': ('96:0', '62:0'),
        'desirable': ('96:0', '62:0'),
        'conditions': (
            'Mana leech needs eligible physical attack damage and target '
            'drain. All resistance is a conditional set bonus, not an '
            'innate property of this belt.',
        ),
        'quality': 'set',
    },
    'Infernostride': {
        'slots': ('Boots',),
        'role': 'Gold Find and fire protection boots',
        'important_stats': ('79:0', '96:0', '39:0', '40:0'),
        'desirable': ('79:0', '39:0', '40:0'),
        'conditions': (
            'The raised fire resistance cap needs actual fire resistance '
            'from the full setup. Wearer Gold Find supports farming; do '
            'not infer additional mercenary Gold Find or a permanently '
            'active Blaze proc.',
        ),
    },
    'Lava Gout': {
        'slots': ('Gloves',),
        'role': 'Attack speed and Enchant-proc gloves',
        'important_stats': ('93:0', '39:0', '118:0', '198:3338'),
        'desirable': ('93:0',),
        'conditions': (
            'Enchant requires a successful on-striking proc; it is not a '
            'guaranteed permanent buff. IAS supports the full Strafe '
            'attack-speed setup. Half Freeze Duration is not Cannot Be '
            'Frozen.',
        ),
    },
    'Manald Heal': {
        'slots': ('Rings',),
        'role': 'Mana sustain ring alternative',
        'important_stats': ('62:0', '74:0', '7:0', '27:0', '105:0'),
        'desirable': ('62:0', '27:0'),
        'conditions': (
            'Mana leech uses the physical javelin hit, not Lightning Fury '
            'lightning damage, and depends on target drain. Highlight '
            'casting speed only when captured; legacy copies may differ. '
            'Casting speed supports casting or teleport, not javelin '
            'attacks.',
        ),
    },
    'Homunculus': {
        'slots': ('Off-Hand',),
        'role': 'Necromancer skill and blocking shield',
        'important_stats': ('83:2', '188:16', '102:0', '20:0', '1:0', '27:0', '138:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('83:2', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Necromancer skills support Poison Nova; curse skill levels '
            'support curse utility separately. Maximum block requires '
            'character level and Dexterity; no socket filler is assumed. '
            'Mana after each kill needs wearer kill credit.',
        ),
        'classes': ('Necromancer',),
        'allowed_sockets': (0, 1),
    },
    'Darkforce Spawn': {
        'slots': ('Off-Hand',),
        'role': 'Necromancer casting and skill-tree shield',
        'important_stats': ('188:17', '188:16', '188:18', '105:0', '77:0'),
        'desirable': ('188:17', '105:0'),
        'conditions': (
            'Prioritize the Poison and Bone roll for Poison Nova. Curse '
            'and Summoning rolls support their own trees, not equal Poison '
            'Nova damage. Check the casting breakpoint and defenses lost '
            'versus other shields; no socket filler is assumed.',
        ),
        'classes': ('Necromancer',),
        'allowed_sockets': (0, 1),
    },
    "Que-Hegan's Wisdom": {
        'slots': ('Body Armor', 'Body Armors'),
        'allowed_sockets': (0, 1),
        'role': 'Skill, casting and recovery armor alternative',
        'important_stats': ('127:0', '105:0', '99:0', '138:0', '35:0', '1:0', '16:0'),
        'desirable': ('127:0', '105:0', '99:0'),
        'conditions': (
            'Faster Cast Rate supports spells and teleport, not weapon attacks. Check full casting and '
            'recovery breakpoints. Mana after each kill requires wearer kill credit. The armor has no native'
            ' resistances; do not infer socket additions.',
        ),
    },
    "Death's Fathom": {
        'classes': ('Sorceress',),
        'slots': ('Weapon',),
        'allowed_sockets': (0, 1),
        'casting_only': True,
        'role': 'Cold spell damage weapon',
        'important_stats': ('83:1', '331:0', '105:0', '39:0', '41:0'),
        'desirable': ('83:1', '331:0'),
        'conditions': (
            'Cold skill damage and Sorceress skills support Blizzard; Faster Cast Rate affects its casting '
            'animation, not the casting delay itself. Ethereal spell casting does not consume weapon '
            'durability. No cold facet is assumed; native resistance rolls remain separate from cold damage.',
        ),
    },
    'Snowclash': {
        'classes': ('Sorceress',),
        'slots': ('Belts',),
        'role': 'Blizzard skills and cold protection belt',
        'important_stats': ('107:59', '107:55', '107:60', '149:0', '44:0'),
        'desirable': ('107:59', '149:0', '44:0'),
        'conditions': (
            'Blizzard and Glacial Spike skill bonuses improve those skills; bonus levels do not supply '
            'hard-point synergies. Chilling Armor must be cast. Cold absorb is flat; the higher resistance '
            'cap still needs actual cold resistance. Added cold weapon damage and the when-struck proc are '
            'not Blizzard spell-damage rolls.',
        ),
    },
    "Gerke's Sanctuary": {
        'slots': ('Off-Hand',),
        'allowed_sockets': (0, 1),
        'role': 'Flat damage reduction and blocking shield alternative',
        'important_stats': ('34:0', '35:0', '20:0', '39:0', '41:0', '43:0', '45:0', '74:0'),
        'desirable': ('34:0', '35:0', '20:0'),
        'conditions': (
            'Physical and magic damage reductions are flat amounts, not percentages. Shield block needs '
            'level and Dexterity from the full setup; no maximum block or Energy Shield is assumed. Compare '
            'substantial Strength requirements and lost casting speed. No socket filler is assumed.',
        ),
    },
    'Herald of Zakarum': {
        'classes': ('Paladin',),
        'slots': ('Off-Hand', 'Off-Hand-Swap'),
        'allowed_sockets': (0, 1),
        'role': 'Paladin combat skills and resistance shield alternative',
        'important_stats': ('83:3', '188:24', '102:0', '20:0', '0:0', '3:0', '39:0', '41:0', '43:0', '45:0', '16:0'),
        'desirable': ('83:3', '188:24', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Skills and resistances apply only while this shield is active. Attack Rating does not improve '
            'Smite, Blessed Hammer or Fist of the Heavens. Upgrading to Zakarum Shield changes Smite damage '
            'and equip requirements; Enhanced Defense does not increase Smite damage. Block depends on level'
            ' and Dexterity. No socket filler or maximum block is assumed.',
        ),
    },
    "Dracul's Grasp": {
        'slots': ('Gloves',),
        'role': 'Life Tap and Open Wounds gloves alternative',
        'important_stats': ('198:5258', '135:0', '0:0', '86:0'),
        'desirable': ('198:5258', '135:0'),
        'build_stats': {
            'dragon-talon-assassin': {'class': 'Assassin', 'keys': ('60:0',)},
            'dream-paladin': {'class': 'Paladin', 'keys': ('60:0',)},
        },
        'conditions': (
            'Life Tap is a chance-to-cast curse on eligible striking attacks, including Smite and kicks, not'
            ' a guaranteed active buff; another curse can overwrite it. Smite can heal through Life Tap but '
            'cannot use ordinary life leech. Ordinary life leech for other attacks depends on physical '
            'damage and target drain. Open Wounds supports eligible hits; Life after each kill requires '
            'wearer kill credit. These gloves provide no Increased Attack Speed.',
        ),
    },
    'Spectral Shard': {
        'slots': ('Weapon',),
        'allowed_sockets': (0, 1),
        'casting_only': True,
        'role': 'Casting speed and resistance weapon alternative',
        'important_stats': ('105:0', '9:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('105:0',),
        'conditions': (
            'This is a casting alternative: Faster Cast Rate supports spells and teleport, not weapon '
            'attacks. Its Attack Rating does not improve spells. Ethereal casting does not consume weapon '
            'durability; attacking does. Compare the complete casting breakpoint and equip requirements; no '
            'socket filler is assumed.',
        ),
    },
    'Bloodfist': {
        'slots': ('Gloves',),
        'role': 'Life and hit recovery glove alternative',
        'important_stats': ('7:0', '99:0'),
        'desirable': ('7:0', '99:0'),
        'build_stats': {
            'dream-paladin': {'class': 'Paladin', 'keys': ('93:0', '21:0')},
            'smite-paladin': {'class': 'Paladin', 'keys': ('93:0',)},
        },
        'conditions': (
            'Hit recovery depends on the full setup. Increased Attack Speed helps attacks, not spell '
            'casting. Added minimum weapon damage does not improve Smite or spells; it is relevant to direct'
            ' weapon attacks. Upgrading changes defense and requirements, not these fixed life/recovery '
            'bonuses.',
        ),
    },
    "Eschuta's Temper": {
        'classes': ('Sorceress',),
        'slots': ('Weapon',),
        'allowed_sockets': (0, 1),
        'casting_only': True,
        'role': 'Elemental casting weapon alternative',
        'important_stats': ('83:1', '105:0', '1:0'),
        'desirable': ('83:1', '105:0'),
        'build_stats': {
            'enchant-sorceress': {'class': 'Sorceress', 'keys': ('329:0',)},
            'meteor-sorceress': {'class': 'Sorceress', 'keys': ('329:0',)},
            'lightning-sorceress': {'class': 'Sorceress', 'keys': ('330:0',)},
        },
        'conditions': (
            'Prioritize the damage roll for the build element; the other element is not a universal premium.'
            ' Elemental skill damage adds to applicable mastery bonuses, not an independent final '
            'multiplier. Ethereal spell casting does not consume durability; attacking does. No facet or '
            'complete casting breakpoint is assumed.',
        ),
    },
    "Immortal King's Detail": {
        'quality': 'set',
        'slots': ('Belts',),
        'role': 'Strength and resistance belt alternative',
        'important_stats': ('0:0', '39:0', '41:0', '31:0'),
        'desirable': ('0:0', '39:0', '41:0'),
        'conditions': (
            'This standalone belt supplies Strength, fire/lightning resistance and flat defense. Conditional'
            ' set hit recovery, extra defense, damage reduction and full-set bonuses require companion '
            'pieces and are not inferred. Check the War Belt equip requirement before relying on its '
            'Strength.',
        ),
    },
    "Natalya's Soul": {
        'quality': 'set',
        'slots': ('Boots',),
        'role': 'Movement and elemental resistance boots alternative',
        'important_stats': ('96:0', '41:0', '43:0'),
        'desirable': ('96:0', '41:0', '43:0'),
        'conditions': (
            'Native movement and cold/lightning resistance do not require other set '
            'pieces. Full-set damage reduction and other conditional bonuses are not '
            'inferred.',
        ),
    },
    "Sander's Riprap": {
        'quality': 'set',
        'slots': ('Boots',),
        'role': 'Movement and attributes boots alternative',
        'important_stats': ('96:0', '0:0', '2:0', '19:0'),
        'desirable': ('96:0',),
        'conditions': (
            'Attack Rating helps direct weapon hits, not spells or the guaranteed '
            'explosion component of an exploding projectile. Strength and Dexterity '
            'support equip requirements; no set completion is inferred.',
        ),
    },
    "Trang-Oul's Girth": {
        'quality': 'set',
        'slots': ('Belts',),
        'role': 'Cannot Be Frozen and resources belt alternative',
        'important_stats': ('153:0', '7:0', '9:0', '74:0'),
        'desirable': ('153:0', '7:0'),
        'conditions': (
            'Cannot Be Frozen addresses ordinary chill, not every slowing effect. '
            'The conditional cold resistance bonus needs other set pieces and is '
            'not part of this standalone belt assessment.',
        ),
    },
    "Nosferatu's Coil": {
        'slots': ('Belts',),
        'role': 'Attack speed and sustain belt alternative',
        'important_stats': ('93:0', '60:0', '0:0', '138:0', '150:0'),
        'desirable': ('93:0', '60:0'),
        'conditions': (
            'Life leech needs eligible physical damage and a drainable target; it '
            'does not leech elemental spell damage. Slows Target applies through '
            'eligible attacks and is subject to target limits. Check the complete '
            'attack-speed breakpoint.',
        ),
    },
    'Razortail': {
        'slots': ('Belts',),
        'role': 'Projectile pierce belt alternative',
        'important_stats': ('156:0', '2:0', '22:0'),
        'desirable': ('156:0',),
        'conditions': (
            'Pierce supports eligible projectiles and combines with the skill or weapon '
            'contribution up to the applicable cap; an already capped setup gains no extra '
            'pierce. Added maximum damage affects weapon damage, not Enchant or Lightning '
            'Fury spell damage. Check the whole projectile setup.',
        ),
    },
    'Goblin Toe': {
        'slots': ('Boots',),
        'role': 'Crushing Blow boots alternative',
        'important_stats': ('136:0', '34:0', '35:0'),
        'desirable': ('136:0',),
        'conditions': (
            'Crushing Blow requires eligible attacks, including Smite; ranged attacks '
            'have reduced effect. These boots provide no Faster Run/Walk. Native or '
            'upgraded boots change requirements; no completed attack-speed or survival '
            'setup is inferred.',
        ),
    },
    'Gore Rider': {
        'slots': ('Boots',),
        'role': 'Crushing Blow and Open Wounds boots alternative',
        'important_stats': ('136:0', '135:0', '96:0'),
        'desirable': ('136:0', '135:0'),
        'build_stats': {
            'berserk-barbarian': {'class': 'Barbarian', 'keys': ['141:0']},
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ['141:0']},
            'dream-paladin': {'class': 'Paladin', 'keys': ['141:0']},
            'strafe-amazon': {'class': 'Amazon', 'keys': ['141:0']},
        },
        'conditions': (
            'Crushing Blow and Open Wounds require eligible attacks and can support '
            'Smite; Deadly Strike does not improve Smite or kicks. Ranged Crushing Blow '
            'has reduced effect. Upgrading changes base kick damage and requirements, not '
            'the innate proc chances.',
        ),
    },
    "Moser's Blessed Circle": {
        'slots': ('Off-Hand', 'Off-Hand Swap', 'Off-Hand-Swap'),
        'allowed_sockets': (2,),
        'role': 'Resistance and blocking shield alternative',
        'important_stats': ('39:0', '41:0', '43:0', '45:0', '20:0', '102:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0', '20:0', '102:0'),
        'conditions': (
            'Two native sockets provide customization; no Perfect Diamonds, '
            'runes or jewels are assumed present. Socket additions must be '
            'checked separately. Increased blocking and faster block rate do '
            'not establish maximum block without character level, Dexterity '
            'and the full loadout. Upgrading changes requirements and base '
            'blocking.',
        ),
    },
    'Lidless Wall': {
        'slots': ('Off-Hand', 'Off-Hand Swap', 'Off-Hand-Swap'),
        'allowed_sockets': (0, 1),
        'role': 'Casting and skill shield alternative',
        'important_stats': ('127:0', '105:0', '77:0', '1:0', '138:0'),
        'desirable': ('127:0', '105:0'),
        'conditions': (
            'Shield bonuses apply only while its weapon set is active. All Skills can '
            'support Call to Arms buffs only when that weapon is actually present; it '
            'does not grant Battle Orders by itself. Faster Cast Rate speeds casting, '
            'not attacks or trap placement. Mana after each kill requires credited '
            'kills and is not mana leech. Check equipment requirements and do not '
            'assume a socket filler.',
        ),
    },
    "Highlord's Wrath": {
        'slots': ('Amulets',),
        'allowed_sockets': (0,),
        'role': 'Attack speed and skill amulet alternative',
        'important_stats': ('127:0', '93:0', '41:0'),
        'desirable': ('127:0', '93:0'),
        'build_stats': {
            'berserk-barbarian': {'class': 'Barbarian', 'keys': ['250:0']},
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ['250:0']},
            'dream-paladin': {'class': 'Paladin', 'keys': ['250:0']},
            'enchant-sorceress': {'class': 'Sorceress', 'keys': ['250:0']},
            'lightning-fury-amazon-guide': {'class': 'Amazon', 'keys': ['250:0']},
            'lightning-strike-amazon': {'class': 'Amazon', 'keys': ['250:0']},
            'strafe-amazon': {'class': 'Amazon', 'keys': ['250:0']},
        },
        'conditions': (
            'Deadly Strike applies to eligible weapon physical damage, not '
            'elemental spell damage or Dragon Talon kicks. Its level-scaled chance '
            'is not an independent multiplicative chance on top of Critical Strike. '
            'Check actual attack-speed breakpoints.',
        ),
    },
    "The Cat's Eye": {
        'slots': ('Amulets',),
        'allowed_sockets': (0,),
        'role': 'Attack speed and movement amulet alternative',
        'important_stats': ('93:0', '96:0', '2:0', '31:0', '32:0'),
        'desirable': ('93:0', '96:0'),
        'conditions': (
            'Dexterity can support equipment, attack rating and shield block; it does '
            'not imply a universal spell or kick damage bonus. Verify complete-loadout '
            'attack speed and block.',
        ),
    },
    'Metalgrid': {
        'slots': ('Amulets',),
        'allowed_sockets': (0,),
        'role': 'Resistance and defense amulet alternative',
        'important_stats': ('31:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0'),
        'build_stats': {
            'berserk-barbarian': {'class': 'Barbarian', 'keys': ['19:0']},
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ['19:0']},
            'dragon-talon-assassin': {'class': 'Assassin', 'keys': ['19:0']},
            'strafe-amazon': {'class': 'Amazon', 'keys': ['19:0']},
        },
        'conditions': (
            'Attack Rating helps eligible attacks, not Smite or spells. Iron Golem and '
            'Iron Maiden charges require separate charge, summon and survival checks; '
            'merely wearing this amulet does not establish an active golem or aura.',
        ),
    },
    "Seraph's Hymn": {
        'slots': ('Amulets',),
        'classes': ('Paladin',),
        'allowed_sockets': (0,),
        'role': 'Paladin skill amulet alternative',
        'important_stats': ('127:0', '188:26'),
        'desirable': ('127:0',),
        'build_stats': {'dream-paladin': {'class': 'Paladin', 'keys': ['121:0', '122:0', '123:0', '124:0']}},
        'conditions': (
            'Defensive Aura skills require the relevant aura to be used. Damage and '
            'Attack Rating against demons/undead support eligible weapon attacks, not '
            'Blessed Hammer, Fist of the Heavens or Smite.',
        ),
    },
    'Telling of Beads': {
        'quality': 'set',
        'slots': ('Amulets',),
        'allowed_sockets': (0,),
        'role': 'Skill and resistance set amulet alternative',
        'important_stats': ('127:0', '43:0', '45:0'),
        'desirable': ('127:0', '43:0', '45:0'),
        'conditions': (
            'Only standalone skill and resistance benefits are assessed; partial or '
            'complete Disciple set bonuses need actual companion pieces.',
        ),
    },
    "Nature's Peace": {
        'slots': ('Rings',),
        'allowed_sockets': (0,),
        'role': 'Corpse control and protection ring alternative',
        'important_stats': ('108:0', '34:0', '45:0'),
        'desirable': ('108:0', '45:0'),
        'conditions': (
            'Slain Monsters Rest in Peace applies to eligible kills by the wearer, '
            'not kills by mercenaries or summons, and prevents reuse of affected '
            'corpses. Flat physical damage reduction is not percent reduction. '
            'Prevent Monster Heal is not universal boss protection. Oak Sage charges '
            'need an actual living summon and available charges; no life bonus is '
            'inferred from ownership.',
        ),
    },
    'The Oculus': {
        'slots': ('Weapon',),
        'classes': ('Sorceress',),
        'allowed_sockets': (0, 1),
        'casting_only': True,
        'role': 'Sorceress casting and Magic Find orb alternative',
        'important_stats': ('83:1', '105:0', '80:0', '39:0', '41:0', '43:0', '45:0', '3:0', '1:0', '138:0'),
        'desirable': ('83:1', '105:0', '80:0'),
        'conditions': (
            'Chance to cast Teleport when struck can move the wearer unexpectedly. '
            'Casting alone does not consume weapon durability, so an ethereal casting '
            'copy remains usable; melee attacks are a separate durability concern. Check '
            'the complete casting breakpoint and do not assume a socket filler.',
        ),
    },
    "Tal Rasha's Guardianship": {
        'quality': 'set',
        'slots': ('Body Armor', 'Body Armors'),
        'role': 'Magic Find and resistance set armor alternative',
        'important_stats': ('80:0', '35:0', '39:0', '41:0', '43:0'),
        'desirable': ('80:0', '39:0', '41:0', '43:0'),
        'conditions': (
            'Set casting and extra Magic Find bonuses require actual companion pieces; '
            'the armor alone does not establish a partial or complete set.',
        ),
    },
    "Tal Rasha's Adjudication": {
        'quality': 'set',
        'classes': ('Sorceress',),
        'slots': ('Amulets',),
        'allowed_sockets': (0,),
        'role': 'Sorceress skill and resource set amulet alternative',
        'important_stats': ('83:1', '7:0', '9:0', '41:0'),
        'desirable': ('83:1',),
        'conditions': (
            'Set casting and other bonuses require actual companion pieces. '
            'Added lightning attack damage does not increase Sorceress spell damage.',
        ),
    },
    "Tal Rasha's Fine-Spun Cloth": {
        'quality': 'set',
        'classes': ('Sorceress',),
        'slots': ('Belts',),
        'role': 'Magic Find and resource set belt alternative',
        'important_stats': ('80:0', '9:0', '2:0', '114:0'),
        'desirable': ('80:0',),
        'conditions': (
            'Set defense and casting bonuses require actual companion pieces. '
            'Damage Taken Goes to Mana restores mana from eligible damage; it does not reduce that damage.',
        ),
    },
    "Tal Rasha's Lidless Eye": {
        'quality': 'set',
        'classes': ('Sorceress',),
        'slots': ('Weapon',),
        'role': 'Casting and elemental mastery set orb alternative',
        'important_stats': ('105:0', '7:0', '9:0', '1:0'),
        'desirable': ('105:0',),
        'build_stats': {
            'blizzard-sorceress': {'class': 'Sorceress', 'keys': ('107:65',)},
            'lightning-sorceress': {'class': 'Sorceress', 'keys': ('107:63',)},
            'meteor-sorceress': {'class': 'Sorceress', 'keys': ('107:61',)},
        },
        'conditions': (
            'Set skills and elemental bonuses require actual companion pieces. '
            'Prioritize the mastery matching the reviewed build element.',
        ),
    },
    'Gull': {
        'slots': ('Weapon-Swap',),
        'role': 'Magic Find weapon swap alternative',
        'important_stats': ('80:0',),
        'desirable': ('80:0',),
        'casting_only': True,
        'allowed_sockets': (0, 1),
        'conditions': (
            'Magic Find applies on the active weapon set at the kill or Find Item; '
            'an inactive swap grants no loot bonus.',
            'Passive or casting use: ethereal durability is not consumed; attacks cannot be repaired. '
            'This role does not endorse weapon damage or infer socket contents.',
        ),
    },
    'Blade of Ali Baba': {
        'slots': ('Weapon', 'Off-Hand', 'Weapon-Swap', 'Off-Hand-Swap'),
        'role': 'Level-scaled loot bonus weapon alternative',
        'important_stats': ('240:0',),
        'desirable': ('240:0',),
        'build_stats': {'gold-find-barbarian': {'class': 'Barbarian', 'keys': ('239:0',)}},
        'casting_only': True,
        'allowed_sockets': (2,),
        'conditions': (
            'Loot bonuses scale with character level and apply on the active weapon set at the kill '
            'or Find Item; an inactive swap grants no loot bonus.',
            'Passive or casting use: ethereal durability is not consumed; attacks cannot be repaired. '
            'This role does not endorse weapon damage. Two sockets may be empty or filled; '
            'Ist, Lem or jewels are not assumed from the item name.',
        ),
    },
    'Magefist': {
        'slots': ('Gloves',),
        'role': 'Casting speed and mana regeneration glove alternative',
        'important_stats': ('105:0', '27:0'),
        'desirable': ('105:0',),
        'build_stats': {
            'enchant-sorceress': {'class': 'Sorceress', 'keys': ('126:1',)},
            'fire-blast-assassin': {'class': 'Assassin', 'keys': ('126:1',)},
            'fire-warlock-guide': {'class': 'Warlock', 'keys': ('126:1',)},
            'fissure-druid': {'class': 'Druid', 'keys': ('126:1',)},
            'meteor-sorceress': {'class': 'Sorceress', 'keys': ('126:1',)},
            'wake-of-fire-assassin': {'class': 'Assassin', 'keys': ('126:1',)},
        },
        'conditions': (
            'Faster Cast Rate affects spells and teleport, not attacks or trap laying. '
            'Added fire attack damage does not increase spell damage.',
        ),
    },
    'Peasant Crown': {
        'slots': ('Helmets',),
        'role': 'Skill and movement progression helmet alternative',
        'important_stats': ('127:0', '96:0', '3:0', '1:0', '74:0'),
        'desirable': ('127:0', '96:0'),
        'conditions': ('Compare resistances and defensive needs in the full setup.',),
    },
    'Tarnhelm': {
        'slots': ('Helmets',),
        'role': 'Skill and Magic Find helmet alternative',
        'important_stats': ('127:0', '80:0'),
        'desirable': ('127:0', '80:0'),
        'conditions': ('Balance Magic Find against clear speed and survival.',),
    },
    'Suicide Branch': {
        'slots': ('Weapon',),
        'role': 'Casting skill and resistance wand alternative',
        'important_stats': ('127:0', '105:0', '77:0', '7:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('127:0', '105:0'),
        'casting_only': True,
        'conditions': (
            'Casting utility only: Faster Cast Rate does not speed up weapon attacks or trap laying. '
            'Ethereal spell casting does not consume durability; melee use cannot be repaired.',
        ),
    },
    'Silkweave': {
        'slots': ('Boots',),
        'role': 'Mana sustain and movement boot alternative',
        'important_stats': ('96:0', '77:0', '138:0', '32:0'),
        'desirable': ('77:0', '138:0'),
        'conditions': ('Mana after each kill requires kills credited to the wearer; it is not mana leech.',),
    },
    'Goldskin': {
        'classes': ('Barbarian',),
        'slots': ('Body Armor',),
        'role': 'Gold Find and resistance armor alternative',
        'important_stats': ('79:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('79:0',),
        'conditions': ('Compare gold yield against survival and clear speed in the intended farming setup.',),
    },
    'Wisp Projector': {
        'slots': ('Rings',),
        'role': 'Lightning absorb ring alternative',
        'important_stats': ('144:0', '80:0'),
        'desirable': ('144:0',),
        'conditions': ('Lightning absorb is a percentage; summon charges are not passive equipped bonuses.',),
    },
    'Frostburn': {
        'slots': ('Gloves',),
        'role': 'Maximum mana glove alternative',
        'important_stats': ('77:0',),
        'desirable': ('77:0',),
        'conditions': ('Compare total mana and the casting breakpoint lost when replacing Faster Cast Rate gloves.',),
    },
    'Chance Guards': {
        'slots': ('Gloves',),
        'role': 'Magic Find glove alternative',
        'important_stats': ('80:0',),
        'desirable': ('80:0',),
        'build_stats': {'gold-find-barbarian': {'class': 'Barbarian', 'keys': ('79:0',)}},
        'conditions': ('Balance Magic Find against clear speed and survival.',),
    },
    'Goldwrap': {
        'slots': ('Belts',),
        'role': 'Magic Find belt alternative',
        'important_stats': ('80:0',),
        'desirable': ('80:0',),
        'build_stats': {
            'gold-find-barbarian': {'class': 'Barbarian', 'keys': ('79:0',)},
            'berserk-barbarian': {'class': 'Barbarian', 'keys': ('93:0',)},
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ('93:0',)},
            'dream-paladin': {'class': 'Paladin', 'keys': ('93:0',)},
            'strafe-amazon': {'class': 'Amazon', 'keys': ('93:0',)},
            'mirrored-blades-warlock-guide': {'class': 'Warlock', 'keys': ('93:0',)},
            'fire-blast-assassin': {'class': 'Assassin', 'keys': ('93:0',)},
            'lightning-sentry-assassin': {'class': 'Assassin', 'keys': ('93:0',)},
            'wake-of-fire-assassin': {'class': 'Assassin', 'keys': ('93:0',)},
        },
        'conditions': (
            'Attack or trap-laying speed depends on the full setup; IAS does not improve spell casting. '
            'Upgrading the Heavy Belt increases potion capacity and equip requirements.',
        ),
    },
    'Dwarf Star': {
        'slots': ('Rings',),
        'role': 'Fire absorb and life ring alternative',
        'important_stats': ('142:0', '35:0', '7:0'),
        'desirable': ('142:0', '35:0'),
        'build_stats': {'gold-find-barbarian': {'class': 'Barbarian', 'keys': ('79:0',)}},
        'conditions': ('Fire absorb is a percentage; Magic Damage Reduced is a flat amount.',),
    },
    "Verdungo's Hearty Cord": {
        'slots': ('Belts',),
        'role': 'Physical damage reduction and life belt alternative',
        'important_stats': ('36:0', '3:0', '99:0', '74:0'),
        'desirable': ('36:0', '3:0'),
        'conditions': (
            'Vitality benefits the player; physical damage reduction is distinct from elemental resistance.',
        ),
    },
    'String of Ears': {
        'slots': ('Belts',),
        'role': 'Physical and magic damage reduction belt alternative',
        'important_stats': ('36:0', '35:0'),
        'desirable': ('36:0', '35:0'),
        'build_stats': {
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ('60:0',)},
            'dragon-talon-assassin': {'class': 'Assassin', 'keys': ('60:0',)},
            'dream-paladin': {'class': 'Paladin', 'keys': ('60:0',)},
        },
        'conditions': ('Life leech requires eligible physical attack damage; spells, traps and Smite do not leech.',),
    },
    "Thundergod's Vigor": {
        'slots': ('Belts',),
        'role': 'Lightning absorb and resistance-cap belt alternative',
        'important_stats': ('42:0', '145:0', '0:0', '3:0'),
        'desirable': ('42:0', '145:0'),
        'build_stats': {
            'lightning-fury-amazon-guide': {'class': 'Amazon', 'keys': ('107:35',)},
            'lightning-strike-amazon': {'class': 'Amazon', 'keys': ('107:34',)},
        },
        'conditions': (
            'The raised lightning cap needs actual lightning resistance. Lightning absorb is a flat amount.',
        ),
    },
    'Wormskull': {
        'classes': ('Necromancer',),
        'slots': ('Helmets',),
        'role': 'Summoner skill and resistance helmet alternative',
        'important_stats': ('83:2', '9:0', '45:0'),
        'desirable': ('83:2',),
        'conditions': ("The wearer's poison attack damage and life leech do not transfer to summoned minions.",),
    },
    'Twitchthroe': {
        'classes': ('Amazon',),
        'slots': ('Body Armor',),
        'role': 'Strafe attack speed and recovery armor alternative',
        'important_stats': ('93:0', '99:0', '0:0', '2:0'),
        'desirable': ('93:0',),
        'conditions': (
            'Increased blocking does not supply block while using a bow; attack speed depends on the full setup.',
        ),
    },
    'The Gnasher': {
        'classes': ('Paladin',),
        'slots': ('Weapon',),
        'role': 'Smite Crushing Blow and Open Wounds alternative',
        'important_stats': ('136:0', '135:0', '0:0'),
        'desirable': ('136:0', '135:0'),
        'conditions': (
            'Weapon Enhanced Damage does not increase Smite damage. '
            'Verify shield, speed and resistances for the encounter.',
        ),
    },
    "Bul-Kathos' Wedding Band": {
        'slots': ('Rings',),
        'role': 'Skill and life ring alternative',
        'important_stats': ('127:0', '216:0'),
        'desirable': ('127:0', '216:0'),
        'conditions': ('Life leech applies to eligible physical attack damage, not spell damage or Smite.',),
    },
    "Skullder's Ire": {
        'allowed_sockets': (0, 1),
        'slots': ('Body Armor', 'Body Armors'),
        'role': 'Magic Find armor alternative',
        'important_stats': ('127:0', '240:0', '35:0'),
        'desirable': ('127:0', '240:0'),
        'conditions': ('Magic Find scales with wearer level; ethereal use relies on the armor repairing itself.',),
    },
    'Wizardspike': {
        'slots': ('Weapon', 'Weapon-Swap', 'Off-Hand-Swap'),
        'role': 'Casting and resistance weapon alternative',
        'important_stats': ('105:0', '39:0', '41:0', '43:0', '45:0', '217:0', '77:0', '27:0'),
        'desirable': ('105:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Faster Cast Rate supports spells and teleport; it does not speed up weapon attacks or trap laying. '
            'Swap benefits apply only while that weapon set is active.',
        ),
    },
}


def expand_named_utility(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['class'] not in CLASS_NAMES
        or row['class'] not in MEMBERS[name].get('classes', CLASS_NAMES)
        or row['side'] != 'player'
        or row['slot'] not in MEMBERS[name]['slots']
    ):
        raise ValueError('Invalid named player utility template membership')
    member = MEMBERS[name]
    additional = member.get('build_stats', {}).get(row['build'], {})
    if additional and row['class'] != additional['class']:
        raise ValueError('Build-specific stat review has the wrong player class')
    quality = member.get('quality', 'unique')
    definition = catalog().named[quality, name]
    base = definition['base_definition']
    nonethereal = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = nonethereal
    if name == "Skullder's Ire":
        durability = {
            'any': [
                nonethereal,
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                        {'op': 'stat_at_least', 'key': '252:0', 'value': 1, 'absent_is_zero': True},
                    ]
                },
            ]
        }
    elif member.get('allow_indestructible'):
        durability = {
            'any': [
                nonethereal,
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                        {'op': 'stat_at_least', 'key': '152:0', 'value': 1, 'absent_is_zero': True},
                    ]
                },
            ]
        }
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name, quality),
    ]
    if not member.get('casting_only') and row['build'] not in member.get('casting_only_builds', ()):
        must.append(durability)
    if 'allowed_sockets' in member:
        must.append({'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in member['allowed_sockets']]})
    if base['type'] in ('ring', 'belt', 'glov', 'boot'):
        must.extend(
            [
                {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
            ]
        )
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [base['type']],
        'qualities': [quality],
        'must': {'all': must},
        'important_stats': [*member['important_stats'], *additional.get('keys', ())],
        'conditions': [*member['conditions'], *row.get('conditions', [])],
    }
