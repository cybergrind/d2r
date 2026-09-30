"""Source-specific completed melee recipes; their bases and attack mechanics differ."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Rift': {
        'types': ('pole', 'scep'),
        'builds': ('mirrored-blades-warlock-guide',),
        'role': 'Experimental Mirrored Blades proc weapon option',
        'important': (
            '198:15696',
            '195:4117',
            '52:0',
            '53:0',
            '48:0',
            '49:0',
            '114:0',
            '0:0',
            '1:0',
            '2:0',
            '3:0',
            '119:0',
        ),
        'attacks': (),
        'conditions': (
            'The guide offers Rift as an experiment, not an optimized full setup. Mirrored Blades can '
            'trigger on-attack Frozen Orb and on-striking Tornado; their chances and damage are separate '
            'from weapon attack damage. No skill synergy or guaranteed proc is inferred. This does not '
            'apply to Echoing Strike. Damage Taken Goes To Mana is recovery, not absorption. Iron Maiden '
            'charges require a separate cast; use a non-ethereal repairable weapon.',
        ),
    },
    'Destruction': {
        'types': ('pole', 'swor'),
        'builds': ('mirrored-blades-warlock-guide',),
        'role': 'Experimental Mirrored Blades proc weapon option',
        'important': (
            '198:14679',
            '195:3094',
            '198:15628',
            '17:0',
            '18:0',
            '52:0',
            '53:0',
            '136:0',
            '141:0',
            '62:0',
            '115:0',
            '2:0',
        ),
        'attacks': (),
        'conditions': (
            'The guide offers Destruction as an experiment, not an optimized full setup. Mirrored Blades '
            'can trigger on-attack Nova and on-striking Molten Boulder/Volcano. The death-triggered Meteor '
            'is not ordinary attack uptime. Weapon ED, Crushing Blow, Deadly Strike and physical mana '
            'leech remain distinct from triggered spells. Ignore Target Defense does not cover every '
            'boss. This does not transfer procs to Echoing Strike; use a non-ethereal repairable weapon.',
        ),
    },
    'Grief': {
        'types': ('swor', 'axe'),
        'important': ('111:0', '93:0'),
        'attacks': ('141:0', '115:0', '116:0'),
        'conditions': (
            'Flat added Damage supports Smite as well as weapon attacks; Deadly Strike, '
            'Ignore Target Defense and target-defense reduction do not improve Smite. '
            'Ignore Target Defense does not cover every boss or unique target. Compare '
            'IAS against the exact weapon/skill breakpoint. An ethereal repairable base '
            'is not a durable player weapon.',
        ),
    },
    'Oath': {
        'types': ('swor', 'axe', 'mace'),
        'indestructible': True,
        'important': ('17:0', '18:0', '93:0', '147:0', '121:0', '123:0'),
        'attacks': (),
        'conditions': (
            'Ethereal Oath is durable through the native Indestructible property, which '
            'must be observed for an ethereal candidate. Enhanced Damage and total IAS '
            'support weapon attacks. Iron Golem and Heart of Wolverine charges do not '
            'mean those summons are active; ethereal charges cannot be repaired/refilled. '
            'Check the documented sword base, hand usage and speed breakpoint.',
        ),
    },
    'Unbending Will': {
        'types': ('swor',),
        'important': ('17:0', '18:0', '93:0', '188:32', '0:0', '3:0', '34:0'),
        'attacks': (),
        'conditions': (
            'Combat skill levels and weapon damage support Barbarian attacks. Ordinary '
            'life leech does not heal converted Berserk magic damage. Taunt is a proc, '
            'not a guaranteed debuff on all targets. Compare the documented sword and '
            'full attack-speed setup; do not infer Non-Ladder recipe availability.',
        ),
    },
    'Death': {
        'types': ('swor', 'axe'),
        'indestructible': True,
        'important': ('136:0',),
        'attacks': (),
        'conditions': (
            'This reviewed Smite alternative prioritizes Crushing Blow. Weapon Enhanced '
            'Damage, Deadly Strike, Attack Rating and mana leech do not improve Smite. '
            'The weapon has no IAS; check the full speed setup. Ethereal use requires '
            'the native Indestructible property. Golem charges are not an active summon.',
        ),
    },
    'Last Wish': {
        'types': ('swor', 'axe', 'hamm'),
        'important': ('136:0', '151:98', '198:5266', '201:17099'),
        'attacks': ('17:0', '18:0', '115:0'),
        'conditions': (
            'Crushing Blow, Might and a Life Tap proc support eligible melee attacks, '
            'including Smite. Fade requires the when-struck proc; neither proc is a '
            'guaranteed active buff. Other curses can replace Life Tap. Weapon Enhanced '
            'Damage and Ignore Target Defense do not improve Smite. The weapon has no '
            'IAS; verify the full speed setup. This review does not infer rune-cost pricing.',
        ),
    },
}


# Build-specific attack mechanics stay separate from the existing Smite review.
BUILD_MEMBERS = {
    ('zeal-paladin', 'Unbending Will'): {
        'types': ('swor',),
        'builds': ('zeal-paladin',),
        'class': 'Paladin',
        'important': (
            '17:0',
            '18:0',
            '93:0',
            '60:0',
            '0:0',
            '3:0',
            '34:0',
            '117:0',
            '19:0',
            '122:0',
            '124:0',
            '22:0',
            '198:8786',
        ),
        'attacks': (),
        'conditions': (
            'ED and IAS support Zeal physical attacks; leech requires drainable physical hits. '
            'The Barbarian Combat skill bonus does not grant Paladin skills. Taunt needs a hit proc '
            'and is not a guaranteed debuff on every target. Compare the complete Fanaticism speed '
            'setup and the Phase Blade physical damage; this is a budget alternative, not a best-DPS claim.',
        ),
    },
    ('zeal-paladin', 'Hustle (weapon)'): {
        'types': ('swor',),
        'builds': ('zeal-paladin',),
        'class': 'Paladin',
        'important': ('17:0', '18:0', '93:0', '198:16513', '2:0', '122:0', '124:0'),
        'attacks': (),
        'conditions': (
            'ED and item IAS support Zeal attacks. Burst of Speed requires a hit proc and is temporary, '
            'not permanent item IAS. Level-1 equipped Fanaticism does not add levels to the Paladin '
            'stronger active Fanaticism. This is the weapon recipe, not armor Hustle; compare the '
            'complete speed setup and actual weapon damage.',
        ),
    },
    ('zeal-paladin', 'Death'): {
        'types': ('swor', 'axe'),
        'builds': ('zeal-paladin',),
        'class': 'Paladin',
        'indestructible': True,
        'important': ('17:0', '18:0', '136:0', '250:0', '119:0', '19:0', '62:0', '195:3538'),
        'attacks': (),
        'conditions': (
            'Weapon ED, Crushing Blow, level-scaled Deadly Strike, attack rating and mana leech support '
            'Zeal physical attacks. Death supplies no IAS: check Fanaticism and the full speed setup. '
            'Ethereal use requires observed Indestructible. Glacial Spike requires an attack proc; '
            'the death trigger and golem charges are not ordinary attack buffs.',
        ),
    },
    ('zeal-paladin', 'Breath of the Dying'): {
        'types': ('axe',),
        'builds': ('zeal-paladin',),
        'class': 'Paladin',
        'indestructible': True,
        'important': (
            '17:0',
            '18:0',
            '93:0',
            '60:0',
            '62:0',
            '0:0',
            '2:0',
            '3:0',
            '19:0',
            '116:0',
            '122:0',
            '124:0',
            '117:0',
        ),
        'attacks': (),
        'conditions': (
            'ED and IAS support Zeal physical attacks. Life and mana leech require drainable physical '
            'hits; they do not guarantee healing against every boss. Strength, Dexterity and Vitality '
            'support the player, while Energy is not a priority. Ethereal use requires observed '
            'Indestructible. Undead bonuses are target-specific; Poison Nova requires a kill proc.',
        ),
    },
    ('zeal-paladin', 'Doom'): {
        'types': ('axe',),
        'builds': ('zeal-paladin',),
        'class': 'Paladin',
        'important': ('17:0', '18:0', '93:0', '151:114', '305:0', '127:0', '141:0', '135:0', '117:0'),
        'attacks': (),
        'conditions': (
            'ED, IAS, skills, Deadly Strike and Open Wounds support Zeal. Equipped Holy Freeze supplies '
            'cold damage and control; enemy cold resistance reduction applies to the wielder cold '
            'damage, not physical damage or an ally aura. Doom has no repair or Indestructible property; '
            'use a non-ethereal player weapon. Volcano requires a hit proc, not guaranteed uptime.',
        ),
    },
}


def expand_combat_weapon(row):
    name = row['item']
    member = BUILD_MEMBERS.get((row['build'], name), MEMBERS.get(name))
    if member is None or row['class'] not in CLASS_NAMES or row['side'] != 'player' or row['slot'] != 'Weapon':
        raise ValueError('Invalid player combat weapon membership')
    if 'builds' in member and (row['build'] not in member['builds'] or row['class'] != member.get('class', 'Warlock')):
        raise ValueError('Unreviewed combat attack mode')
    repairable = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = repairable
    if member.get('indestructible'):
        durability = {
            'any': [
                repairable,
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
        durability,
        *[
            {'op': 'fact_eq', 'field': k, 'value': v}
            for k, v in (
                ('identified', True),
                ('runeword', name),
                ('sockets', len(catalog().runewords[name]['runes'])),
                ('socket_contents', 'filled'),
            )
        ],
        legal_base_condition(name, member['types']),
    ]
    important = list(member['important'])
    if row['build'] != 'smite-paladin':
        important.extend(member['attacks'])
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': member.get('role', 'Completed melee weapon alternative'),
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': list(member['types']),
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': important,
        'conditions': [*member['conditions'], *row.get('conditions', [])],
    }
