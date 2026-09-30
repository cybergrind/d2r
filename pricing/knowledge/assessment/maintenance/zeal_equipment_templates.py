"""Reviewed player armor and helmets for physical Zeal, independent of mercenary use."""

from pricing.knowledge.assessment.maintenance.aura_recipe_templates import recipe_condition


RESISTANCES = ('39:0', '41:0', '43:0', '45:0')
MEMBERS = {
    'Enigma': {
        'role': 'Zeal Teleport and magic-find armor alternative',
        'stats': ('127:0', '97:54', '96:0', '220:0', '240:0', '86:0', '31:0', '76:0', '36:0', '114:0'),
        'desirable': ('97:54', '127:0', '220:0', '240:0'),
        'conditions': [
            'Teleport enables travel but still needs mana and a full casting-speed setup. Enigma supplies '
            'no FCR; the guide uses its casting swap to teleport and the main weapon to attack.',
            'Strength and magic find scale with character level. Defense is a flat recipe bonus plus base '
            'defense, not Enhanced Defense. Life after kill requires credited kills and is not boss leech.',
        ],
    },
    'Fortitude': {
        'role': 'Zeal off-weapon physical damage armor alternative',
        'stats': ('17:0', '18:0', '16:0', '105:0', '201:3855', '114:0', '216:0', '34:0', '74:0', '42:0', *RESISTANCES),
        'desirable': ('17:0', '18:0', '216:0', *RESISTANCES),
        'conditions': [
            'Armor Enhanced Damage contributes off-weapon physical damage to Zeal; it is not weapon-base '
            'damage or elemental damage. Weapon and armor rune effects differ.',
            'Chilling Armor needs its when-struck proc and is not assumed active. Life scales with level '
            'and the recipe coefficient. FCR supports casting, not Zeal attack speed; no life leech is supplied.',
        ],
    },
    'Chains of Honor': {
        'role': 'Zeal resistance, skills and leech armor alternative',
        'stats': ('127:0', '16:0', '121:0', '122:0', '60:0', '0:0', '74:0', '36:0', '80:0', *RESISTANCES),
        'desirable': ('127:0', '121:0', '60:0', '36:0', *RESISTANCES),
        'conditions': [
            'Demon and undead damage apply only to the matching target types. Life leech requires eligible '
            'physical hits and target drain effectiveness; it is not guaranteed Uber sustain.',
            'The armor supplies 65 all resistance including Um, but no IAS or Crushing Blow. Skills support '
            'Zeal and Fanaticism; evaluate the complete attack-speed and resistance setup.',
        ],
    },
    'Duress': {
        'role': 'Zeal Crushing Blow and Open Wounds armor alternative',
        'stats': ('17:0', '18:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0', *RESISTANCES),
        'desirable': ('136:0', '135:0', '99:0', *RESISTANCES),
        'conditions': [
            'Crushing Blow and Open Wounds require eligible hits. Off-weapon Enhanced Damage supports '
            'physical Zeal; cold damage is a separate component and can shatter corpses.',
            'Recipe and Shael total 40 FHR; recovery is not attack speed. Resistance includes Um and Thul. '
            'The armor supplies no life leech or Cannot Be Frozen.',
        ],
    },
    'Hustle (armor)': {
        'role': 'Zeal attack-speed and movement armor alternative',
        'stats': ('93:0', '96:0', '99:0', '97:29', '2:0', *RESISTANCES),
        'desirable': ('93:0', '96:0'),
        'conditions': [
            'Armor IAS and movement support the player; attack breakpoints depend on weapon and Fanaticism. '
            'Evade is a player movement defense, not guaranteed protection while attacking.',
            'This is the armor recipe, not weapon Fanaticism or a Burst of Speed proc. Assessment of a '
            'completed Non-Ladder item does not establish current recipe creation availability.',
        ],
    },
    'Lionheart': {
        'role': 'Zeal attributes, life and resistance armor alternative',
        'stats': ('17:0', '18:0', '0:0', '2:0', '3:0', '7:0', '1:0', *RESISTANCES),
        'desirable': ('0:0', '2:0', '3:0', '7:0', *RESISTANCES),
        'conditions': [
            'Player Vitality contributes life; Dexterity supports attack rating and the block setup. '
            'Off-weapon Enhanced Damage is physical, while flat life and resistance provide separate survival.',
            'Fal adds to recipe Strength for 25 total. The armor supplies no IAS, leech or FHR; reduced '
            'requirements do not prove this character can equip the chosen base.',
        ],
    },
    'Smoke': {
        'role': 'Zeal resistance and recovery armor alternative',
        'stats': ('16:0', '32:0', '99:0', '1:0', '204:4614', *RESISTANCES),
        'desirable': (*RESISTANCES, '99:0'),
        'conditions': [
            'Resistance and recovery support player survival; defense versus missiles is not all-purpose '
            'defense. This armor supplies no IAS, leech or Crushing Blow.',
            'Available Weaken charges require deliberate casting and recharge. Depleted or unread charges '
            'do not establish usable Weaken. Applying another curse can replace Life Tap; no curse is assumed active.',
        ],
    },
    'Bulwark': {
        'role': 'Zeal physical reduction and leech helmet alternative',
        'stats': ('76:0', '16:0', '36:0', '74:0', '60:0', '99:0', '3:0', '34:0'),
        'desirable': ('36:0', '60:0', '99:0'),
        'conditions': [
            'Percentage and flat physical reduction are distinct. Player Vitality and maximum life support '
            'survival; life leech still requires drainable physical hits and is not assured boss sustain.',
            'Elemental resistance and attack speed need other gear. Assess an existing completed Non-Ladder '
            'item separately from recipe creation availability.',
        ],
    },
    'Temper': {
        'role': 'Zeal fire resistance and absorb helmet alternative',
        'stats': ('76:0', '16:0', '39:0', '142:0', '99:0', '3:0'),
        'desirable': ('39:0', '142:0', '99:0'),
        'conditions': [
            'Fire resistance includes Ral; percentage fire absorb is separate and does not protect against '
            'other elements. Player Vitality and life support survival; this helmet supplies no life leech.',
            'Assess an existing completed Non-Ladder item separately from recipe creation availability.',
        ],
    },
}


def expand_zeal_equipment(row):
    name = row['item']
    if name not in MEMBERS or row['build'] != 'zeal-paladin' or row['class'] != 'Paladin' or row['side'] != 'player':
        raise ValueError('Unreviewed Zeal equipment use')
    helmet = name in ('Bulwark', 'Temper')
    if row['slot'] not in (('Helmets',) if helmet else ('Body Armor', 'Body Armors')):
        raise ValueError('Unreviewed Zeal equipment slot')
    member = MEMBERS[name]
    types = ['helm', 'circ'] if helmet else ['tors']
    return {
        **{k: v for k, v in row.items() if k not in ('item', 'class', 'template')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': types,
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
                recipe_condition(name, types),
                {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
            ]
        },
        'important_stats': list(member['stats']),
        'conditions': [
            *member['conditions'],
            'This is sustained player equipment, not a mercenary or prebuff-only role. Non-ethereal '
            'durability is required. Check base requirements and the full loadout; no best-base or price '
            'premium is inferred from the recipe name.',
        ],
    }
