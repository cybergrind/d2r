"""Reviewed player recipe utility, separate from empty-base or market appraisal."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Rhyme': {
        'role': 'Caster utility and Magic Find shield alternative',
        'slots': ('Off-Hand', 'Off-Hand-Swap'),
        'types': ('shie',),
        'class_types': {'Necromancer': ['head'], 'Warlock': ['grim']},
        'important_stats': ('153:0', '102:0', '20:0', '39:0', '41:0', '43:0', '45:0', '80:0', '79:0', '27:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0', '80:0'),
        'conditions': (
            'Cannot Be Frozen helps movement but does not increase spell casting speed. Rhyme supplies no FCR. '
            'Block depends on the wearer, Dexterity and level; a Book or Necromancer head has separate native '
            'staffmods that are not assumed from the recipe.',
            'Shield bonuses apply only while that weapon set is active. A normal shield requires a compatible '
            'main weapon; only a Warlock Book permits that class two-handed weapon exception.',
        ),
    },
    'Leaf': {
        'classes': ('Sorceress', 'Warlock', 'Druid'),
        'slots': ('Weapon',),
        'types': ('staf',),
        'role': 'Fire skill staff alternative',
        'important_stats': ('126:1', '43:0', '138:0', '214:0'),
        'desirable': ('126:1', '138:0'),
        'conditions': (
            'Fire skill levels benefit eligible fire skills, not every class skill. '
            'Sorceress Warmth soft levels do not count as Enchant hard-point synergy; '
            'native staffmods are assessed separately. Inserted fire damage is weapon '
            'damage, not a spell multiplier.',
        ),
        'casting_only': True,
        'build_stats': {'enchant-sorceress': {'class': 'Sorceress', 'keys': ('107:37',)}},
    },
    'Obsession': {
        'classes': ('Sorceress', 'Warlock'),
        'slots': ('Weapon',),
        'types': ('staf',),
        'role': 'Casting, recovery and resistance staff alternative',
        'important_stats': (
            '127:0',
            '105:0',
            '99:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '76:0',
            '27:0',
            '80:0',
            '79:0',
            '1:0',
            '3:0',
        ),
        'desirable': ('127:0', '105:0', '99:0', '39:0', '41:0', '43:0', '45:0', '76:0'),
        'conditions': (
            'Native staffmods and actual two-handed equipment compatibility remain '
            'separate. Do not assume the when-struck Weaken proc is active. Zod '
            'supplies indestructibility; inserted knockback does not enhance '
            'casting.',
        ),
        'casting_only': True,
    },
    'Silence': {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'types': ('axe', 'hamm', 'pole', 'spea', 'staf', 'swor'),
        'role': 'Echoing Strike physical damage and resistance weapon alternative',
        'important_stats': (
            '127:0',
            '17:0',
            '18:0',
            '62:0',
            '99:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '80:0',
            '138:0',
            '122:0',
            '124:0',
        ),
        'desirable': ('127:0', '17:0', '18:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Echoing Strike uses FCR, not IAS. Physical leech depends on target and '
            'damage. Blind and flee attack effects do not apply through Echoing Strike. '
            'Six-socket base and actual two-handed/off-hand compatibility matter.',
        ),
        'casting_only': True,
    },
    'Void': {
        'classes': ('Warlock', 'Paladin'),
        'slots': ('Weapon',),
        'types': ('knif',),
        'role': 'Magic casting dagger alternative',
        'important_stats': ('127:0', '105:0', '357:0', '0:0', '1:0', '2:0', '3:0', '80:0'),
        'desirable': ('127:0', '105:0', '357:0'),
        'conditions': (
            'Magic damage supports Abyss, Blessed Hammer or active Hex Purge; it does not '
            'multiply physical Echoing damage. Zod supplies indestructibility. Decrepify '
            'requires casting available charges and is not a passive aura.',
        ),
        'casting_only': True,
        'build_stats': {'abyss-warlock-build-guide': {'class': 'Warlock', 'keys': ('97:402',)}},
    },
    'Plague': {
        'classes': ('Warlock', 'Necromancer'),
        'slots': ('Weapon',),
        'types': ('swor', 'knif'),
        'role': 'Skill and Cleansing casting weapon alternative',
        'important_stats': ('127:0', '151:109'),
        'desirable': ('127:0', '151:109'),
        'conditions': (
            'Cleansing reduces eligible curse/poison durations; it does not grant '
            'immunity. Lower Resist when struck and Poison Nova on striking are not '
            'assumed active. Poison resistance reduction does not boost magic or '
            'physical damage. Echoing uses FCR, not the inserted IAS.',
        ),
        'casting_only': True,
        'build_stats': {
            'echoing-strike-warlock-guide': {'class': 'Warlock', 'keys': ('17:0', '18:0', '250:0')},
            'poison-nova-necromancer': {'class': 'Necromancer', 'keys': ('336:0',)},
        },
    },
    'Crescent Moon': {
        'classes': ('Assassin', 'Sorceress'),
        'slots': ('Weapon', 'Weapon-Swap'),
        'types': ('axe', 'swor', 'pole'),
        'role': 'Lightning resistance reduction weapon alternative',
        'important_stats': ('334:0', '147:0', '138:0'),
        'desirable': ('334:0',),
        'conditions': (
            'Enemy lightning resistance reduction benefits the active wielder, '
            'not a mercenary holding this weapon for the player. Attack procs, '
            'weapon ED and Ignore Target Defense are not spell or trap damage '
            'multipliers. Trap laying uses attack speed; Sorceress casting uses '
            'FCR. Swap use requires the relevant weapon set active.',
        ),
        'casting_only': True,
        'build_stats': {'lightning-sentry-assassin': {'class': 'Assassin', 'keys': ('93:0',)}},
    },
    'Doom': {
        'classes': ('Warlock',),
        'slots': ('Weapon',),
        'types': ('axe', 'hamm', 'pole'),
        'role': 'Echoing physical damage and Holy Freeze utility weapon alternative',
        'important_stats': ('127:0', '17:0', '18:0', '141:0', '151:114'),
        'desirable': ('127:0', '17:0', '18:0', '141:0'),
        'conditions': (
            'Holy Freeze provides target-dependent slowing. Cold resistance reduction '
            'affects applicable cold damage, not physical echoes or Hex Purge magic. IAS, '
            'Open Wounds and on-striking Volcano do not apply through Echoing Strike.',
        ),
        'casting_only': True,
    },
    'Beast': {
        'classes': ('Necromancer',),
        'slots': ('Weapon',),
        'types': ('axe', 'hamm', 'scep'),
        'role': 'Summoner Fanaticism weapon alternative',
        'important_stats': ('151:122', '0:0', '1:0', '138:0'),
        'desirable': ('151:122',),
        'conditions': (
            'Keep Fanaticism active and summons within its radius. The wielder weapon ED, '
            'IAS, Crushing Blow and Open Wounds are not transferred as item stats to '
            'skeletons. This caster role does not authorize melee use of an ethereal '
            'copy; transformation and Grizzly charges are separate utilities.',
        ),
        'casting_only': True,
    },
    'Principle': {
        'classes': ('Paladin',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Paladin skill and life armor alternative',
        'important_stats': ('83:3', '7:0', '39:0', '46:0'),
        'desirable': ('83:3', '7:0'),
        'conditions': (
            'Paladin skills support Hammer and Fist of the Heavens. Damage to Undead '
            'and on-striking Holy Bolt do not multiply either spell. Fire resistance '
            'and maximum poison resistance are separate. No FCR or reliable proc '
            'uptime is supplied.',
        ),
    },
    'Peace': {
        'classes': ('Amazon',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Amazon skill and recovery armor alternative',
        'important_stats': ('83:0', '99:0', '43:0', '97:9'),
        'desirable': ('83:0', '99:0'),
        'conditions': (
            'Amazon skills support lightning attacks. Critical Strike affects the '
            'physical hit, not Lightning Fury or Lightning Strike lightning damage. '
            'Valkyrie requires a proc and appropriate summon conditions; it is not '
            'assumed permanently present. No IAS is supplied.',
        ),
    },
    'Hearth': {
        'classes': ('Assassin', 'Paladin'),
        'slots': ('Helmets',),
        'types': ('helm', 'circ'),
        'role': 'Cold survival and Cannot Be Frozen helmet alternative',
        'important_stats': ('153:0', '43:0', '148:0', '76:0', '16:0', '99:0', '3:0'),
        'desirable': ('153:0', '43:0', '148:0'),
        'conditions': (
            'Cold Absorb is percentage absorption, not flat absorption. Cannot Be Frozen '
            'does not prevent every slow. Assess the full resistance setup and '
            'absorption cap. This assesses a completed item, not Non-Ladder crafting '
            'availability.',
        ),
    },
    'Enlightenment': {
        'classes': ('Sorceress',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Enchant Sorceress skill armor alternative',
        'important_stats': ('83:1', '97:37', '39:0', '34:0', '16:0'),
        'desirable': ('83:1',),
        'conditions': (
            'Sorceress levels improve Enchant; item Warmth levels help mana '
            'regeneration but do not add hard-point Enchant synergy. On-striking '
            'Fire Ball and when-struck Blaze are not always active. No FCR is '
            'supplied.',
        ),
    },
    'Authority': {
        'classes': ('Warlock',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Fire Warlock skill armor alternative',
        'important_stats': ('83:7', '99:0', '39:0'),
        'desirable': ('83:7', '99:0'),
        'conditions': (
            'Warlock levels support the fire skills. Off-weapon Enhanced Damage does '
            'not multiply fire spell damage. Miasma Chains and Psychic Ward require '
            'their triggering events; no permanent proc effect is assumed.',
        ),
    },
    'Rain': {
        'classes': ('Druid',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Fissure skill and mana armor alternative',
        'important_stats': ('83:5', '9:0', '41:0', '35:0', '114:0'),
        'desirable': ('83:5', '9:0'),
        'conditions': (
            'Druid levels support Fissure. Damage Taken Goes to Mana does not absorb '
            'damage. Cyclone Armor requires a when-struck proc and has finite absorption; '
            'it is not assumed active. Twister on striking does not increase Fissure '
            'damage.',
        ),
    },
    'Bramble': {
        'classes': ('Necromancer',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Poison Nova damage armor alternative',
        'important_stats': ('332:0', '99:0', '31:0', '86:0', '45:0', '39:0', '44:0', '77:0', '27:0'),
        'desirable': ('332:0', '99:0'),
        'conditions': (
            'Poison Skill Damage increases Poison Nova damage. Thorns and Spirit of '
            'Barbs do not multiply poison damage; charges require separate use. Life '
            'after each kill requires wearer kill credit. This armor supplies neither '
            'FCR nor Teleport; compare the full casting and travel setup.',
        ),
    },
    'Bone': {
        'classes': ('Necromancer',),
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'role': 'Necromancer skill and resistance armor alternative',
        'important_stats': ('83:2', '9:0', '39:0', '41:0', '43:0', '45:0', '34:0'),
        'desirable': ('83:2', '9:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Necromancer levels support Poison Nova. Bone Armor is a triggered defensive '
            'effect with finite absorption, not a permanent bonus inferred from ownership; '
            'Bone Spear on striking does not multiply poison damage. No FCR is '
            'supplied.',
        ),
    },
    'Sanctuary': {
        'classes': ('Assassin', 'Amazon'),
        'slots': ('Off-Hand',),
        'types': ('shie',),
        'role': 'Resistance and blocking shield alternative',
        'important_stats': ('39:0', '41:0', '43:0', '45:0', '20:0', '102:0', '99:0', '16:0', '32:0', '2:0', '35:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0', '20:0', '99:0'),
        'conditions': (
            'Shield resistance, recovery and blocking are separate survival benefits. '
            'Actual block chance depends on base, Dexterity, level and stance; no '
            'max-block guarantee is inferred. Slow Missiles charges require separate '
            'use and are not assumed active.',
        ),
    },
    'Flickering Flame': {
        'role': 'Fire skill and resistance-piercing helmet',
        'slots': ('Helmets',),
        'types': ('helm', 'circ'),
        'important_stats': ('126:1', '333:0', '151:100', '9:0', '110:0', '118:0'),
        'desirable': ('126:1', '333:0', '151:100'),
        'conditions': (
            'Fire skills and enemy fire resistance reduction support applicable fire damage, including '
            'traps. Enemy resistance reduction does not itself break an immunity. Resist Fire aura applies '
            'while equipped and within range; it does not grant hard-point passive resistance-cap bonuses. '
            'Half Freeze Duration is not Cannot Be Frozen. Druid staffmods are separate base properties; '
            'none are assumed. This assesses a completed item, not Non-Ladder crafting availability.',
        ),
    },
    'Wisdom': {
        'role': 'Cannot Be Frozen and mana helmet alternative',
        'slots': ('Helmets',),
        'types': ('helm', 'circ'),
        'important_stats': ('153:0', '138:0', '1:0'),
        'desirable': ('153:0', '138:0'),
        'build_stats': {
            'double-throw-barbarian-guide': {'class': 'Barbarian', 'keys': ('156:0', '62:0', '119:0')},
            'enchant-sorceress': {'class': 'Sorceress', 'keys': ('156:0', '62:0', '119:0')},
            'lightning-fury-amazon-guide': {'class': 'Amazon', 'keys': ('156:0', '62:0')},
        },
        'conditions': (
            'Pierce supports eligible weapon projectiles, not traps, and provides no extra benefit once '
            'capped. Mana leech requires eligible physical damage and a drainable target; spell/trap damage '
            'does not leech. Attack Rating does not improve Lightning Fury or spells. Mana after each kill '
            'requires wearer kill credit. Cannot Be Frozen does not prevent every slow. This assesses a '
            'completed item, not Non-Ladder crafting availability.',
        ),
    },
    'Memory': {
        'role': 'Energy Shield prebuff',
        'slots': ('Weapon-Swap',),
        'types': ('staf',),
        'classes': ('Sorceress',),
        'casting_only': True,
        'important_stats': ('83:1', '107:58'),
        'desirable': ('83:1', '107:58'),
        'conditions': (
            'Use Memory to cast Energy Shield before switching back. Its Sorceress and Energy '
            'Shield bonuses contribute to the prebuff; Telekinesis synergy depends on actual '
            'hard points, not item skill bonuses. Staffmods can improve the prebuff, but no '
            '+3 Energy Shield base is assumed. Casting does not consume staff durability; '
            'melee use is a separate durability concern.',
        ),
    },
    'Harmony': {
        'role': 'Vigor movement swap',
        'slots': ('Weapon-Swap',),
        'types': ('bow', 'xbow'),
        'class_types': {'Amazon': ['abow']},
        'important_stats': ('151:115',),
        'desirable': ('151:115',),
        'conditions': (
            'Vigor supplies movement only while this weapon set is active and the recipient '
            'is within aura range. This is a movement swap, not a damage-roll or permanent '
            'buff requirement. Revive charges and Valkyrie require separate summon/charge '
            'checks and are not assumed active. Check bow equip requirements.',
        ),
    },
    'Wealth': {
        'role': 'Magic Find and Gold Find armor',
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'important_stats': ('80:0', '79:0', '2:0', '138:0'),
        'desirable': ('80:0', '79:0'),
        'conditions': (
            'Magic Find and Gold Find must be active when rewards are generated. This armor '
            'supplies no resistance or attack speed; verify survival and travel tradeoffs. '
            'Mana after each kill is kill credit, not leech.',
        ),
    },
    'Splendor': {
        'role': 'Casting and skill shield alternative',
        'slots': ('Off-Hand', 'Off-Hand-Swap', 'Off-Hand Swap'),
        'types': ('shie',),
        'class_types': {'Necromancer': ['head'], 'Warlock': ['grim']},
        'important_stats': ('127:0', '105:0', '102:0', '80:0', '79:0', '27:0', '1:0'),
        'desirable': ('127:0', '105:0'),
        'conditions': (
            'Bonuses apply only while this shield is active; All Skills does not grant '
            'Battle Orders without the actual Call to Arms weapon. Faster Cast Rate does '
            'not speed attacks or trap placement. Class-specific shield '
            'staffmods/resistance remain additional base properties, not assumed recipe '
            'bonuses.',
        ),
    },
    'Hustle (armor)': {
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'important_stats': ('93:0', '96:0', '99:0', '39:0', '41:0', '43:0', '45:0', '97:29'),
        'desirable': ('93:0', '96:0'),
        'conditions': (
            'Attack speed breakpoints depend on the weapon, skill and complete loadout. '
            'This armor does not supply the weapon recipe Fanaticism or Burst of Speed proc. '
            'Player armor must be repairable; an ethereal copy is not a durable player alternative. '
            'This assesses an existing completed item, not current Non-Ladder recipe creation availability.',
        ),
    },
    'Lore': {
        'slots': ('Helmets',),
        'types': ('helm', 'circ'),
        'important_stats': ('127:0', '41:0', '34:0', '138:0', '1:0'),
        'desirable': ('127:0', '41:0'),
        'conditions': ('Class-specific helm staffmods are separate from the recipe skill bonus.',),
    },
    'Stealth': {
        'slots': ('Body Armor', 'Body Armors'),
        'types': ('tors',),
        'important_stats': ('96:0', '105:0', '99:0', '45:0', '27:0', '35:0', '2:0'),
        'desirable': ('96:0', '105:0', '99:0'),
        'conditions': (
            'Casting and recovery breakpoints use the full loadout. '
            'Faster Cast Rate does not speed up attacks or trap laying.',
        ),
    },
    "Ancients' Pledge": {
        'slots': ('Off-Hand',),
        'types': ('shie',),
        'important_stats': ('39:0', '41:0', '43:0', '45:0'),
        'desirable': ('39:0', '41:0', '43:0', '45:0'),
        'conditions': ('Resistance utility does not establish maximum block or Cannot Be Frozen.',),
    },
    'Ground': {
        'slots': ('Helmets',),
        'types': ('helm', 'circ'),
        'important_stats': ('41:0', '144:0', '76:0', '99:0', '3:0'),
        'desirable': ('41:0', '144:0'),
        'conditions': (
            'Lightning resistance and absorb address lightning damage; other damage types need separate defenses.',
        ),
    },
}


def expand_progression_equipment(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['class'] not in CLASS_NAMES
        or row['class'] not in MEMBERS[name].get('classes', CLASS_NAMES)
        or row['side'] != 'player'
        or row['slot'] not in MEMBERS[name]['slots']
    ):
        raise ValueError('Invalid player progression equipment membership')
    member = MEMBERS[name]
    additional = member.get('build_stats', {}).get(row['build'], {})
    if additional and row['class'] != additional['class']:
        raise ValueError('Build-specific stat review has the wrong player class')
    types = list(member['types'])
    if 'helm' in types and row['class'] in ('Druid', 'Barbarian'):
        types.append({'Druid': 'pelt', 'Barbarian': 'phlm'}[row['class']])
    if 'shie' in types and row['class'] == 'Paladin':
        types.append('ashd')
    types.extend(member.get('class_types', {}).get(row['class'], ()))
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        *[
            {'op': 'fact_eq', 'field': key, 'value': value}
            for key, value in (
                ('identified', True),
                ('ethereal', False),
                ('runeword', name),
                ('sockets', len(catalog().runewords[name]['runes'])),
                ('socket_contents', 'filled'),
            )
            if key != 'ethereal' or not member.get('casting_only')
        ],
        legal_base_condition(name, types),
    ]
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': member.get('role', 'Player skill and survival progression alternative'),
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': types,
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': [*member['important_stats'], *additional.get('keys', ())],
        'conditions': [*member['conditions'], *row.get('conditions', [])],
    }
