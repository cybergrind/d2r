"""Reviewed mercenary weapon recipes, with bearer and aura recipients kept separate."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Insight': {
        'types': ('pole',),
        'mercenaries': ('Act 2 Might',),
        'important': ('151:120', '17:0', '18:0', '97:9', '119:0', '0:0', '2:0', '21:0'),
        'desirable': ('151:120', '17:0', '18:0', '97:9'),
        'conditions': (
            'Meditation supports nearby allies while the mercenary is alive. Weapon Enhanced Damage, '
            'attack rating and Critical Strike benefit the mercenary physical attacks, not player damage. '
            'Insight supplies no life leech or IAS; verify these and survivability in the remaining gear. '
            'Faster Cast Rate, Energy and Vitality are not mercenary priorities. Native Insight supports '
            'polearms, staves and missile weapons; this Act 2 configuration requires a legal polearm.',
        ),
    },
    'Obedience': {
        'types': ('pole', 'spea'),
        'mercenaries': ('Act 2 Might',),
        'important': ('17:0', '18:0', '136:0', '39:0', '41:0', '43:0', '45:0', '31:0', '99:0', '196:3349'),
        'desirable': ('17:0', '18:0', '136:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': (
            'Enhanced Damage and Crushing Blow affect the mercenary. Enchant requires a '
            'kill-triggered proc and buffs the wielder, not the player. Enemy fire resistance '
            'reduction is local to mercenary damage. The weapon supplies no life leech or '
            'IAS; check both elsewhere in the loadout.',
        ),
    },
    'Pride': {
        'types': ('pole', 'spea'),
        'mercenaries': ('Act 2 Might',),
        'important': ('151:113', '119:0', '141:0', '74:0'),
        'desirable': ('151:113',),
        'conditions': (
            'Concentration supports eligible allied damage while the mercenary is alive '
            'and recipients are within aura range. This weapon has no native weapon '
            'Enhanced Damage, IAS or life leech; mercenary damage and sustain can suffer. '
            'Freeze Target may destroy corpses needed for corpse skills; blind can interfere '
            'with curses on eligible targets. Do not infer complete aura uptime.',
        ),
    },
    'Breath of the Dying': {
        'types': ('pole', 'spea'),
        'mercenaries': ('Act 2 Might', 'Act 2 Prayer'),
        'important': ('17:0', '18:0', '93:0', '60:0', '0:0', '2:0', '122:0'),
        'desirable': ('17:0', '18:0', '93:0', '60:0'),
        'conditions': (
            'Weapon damage, IAS and life leech support mercenary attacks; leech still '
            'depends on physical damage and target drain effectiveness. Strength and '
            'Dexterity support requirements and attacks. Vitality, Energy and mana leech '
            'do not supply mercenary resources; Prevent Monster Heal is not credited to '
            'the mercenary. This review does not transfer the weapon bonuses to the player.',
        ),
    },
    'Faith': {
        'types': ('bow', 'abow'),
        'mercenaries': ('Act 1 Fire', 'Act 1 Cold'),
        'important': ('151:122', '127:0', '17:0', '18:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('151:122',),
        'conditions': (
            'Fanaticism supports allies only while the Rogue is alive and in aura range. '
            'Its rolled aura level is not raised by the weapon All Skills; All Skills '
            'supports the mercenary skills separately. Bow damage and resistances belong '
            'to the Rogue. Rogues cannot use crossbows; bows are non-ethereal. Check the '
            'player attack-speed breakpoint using the actual aura roll.',
        ),
    },
}


def expand_merc_weapon(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['class'] not in CLASS_NAMES
        or row['side'] != 'merc'
        or row['slot'] != 'Weapon'
        or row.get('mercenary_type') not in MEMBERS[name]['mercenaries']
    ):
        raise ValueError('Invalid reviewed mercenary weapon membership')
    member = MEMBERS[name]
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'context_eq', 'field': 'mercenary_type', 'value': row['mercenary_type']},
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
    if name == 'Faith':
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Mercenary weapon and aura alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': list(member['types']),
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': list(member['important']),
        'conditions': [
            'Verify mercenary level and equip requirements. Ethereal durability is safe '
            'for eligible mercenary weapons; no universal price premium is inferred.',
            *member['conditions'],
            *row.get('conditions', []),
        ],
    }


def expand_named_merc_weapon(row):
    """Named polearm alternatives share no player durability or aura assumptions."""
    from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition

    name = row['item']
    if (
        name != "The Reaper's Toll"
        or row['class'] not in CLASS_NAMES
        or row['side'] != 'merc'
        or row['slot'] != 'Weapon'
        or row.get('mercenary_type') not in ('Act 2 Might', 'Act 2 Defiance')
    ):
        raise ValueError('Invalid reviewed named mercenary weapon use')
    definition = catalog().named['unique', name]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Mercenary Decrepify and physical sustain alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
                {'op': 'context_eq', 'field': 'mercenary_type', 'value': row['mercenary_type']},
                {'op': 'fact_eq', 'field': 'identified', 'value': True},
                named_base_condition(name),
                {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in (0, 1)]},
            ]
        },
        'important_stats': ['17:0', '18:0', '198:5569', '60:0', '141:0', '115:0', '54:0', '55:0'],
        'conditions': [
            'Decrepify requires a mercenary hit proc and can overwrite Amplify Damage or other curses. '
            'It supports eligible physical damage, not fire or lightning resistance reduction.',
            'Weapon damage, life leech and Deadly Strike belong to the mercenary. Ethereal durability '
            'is safe here; Ignore Target Defense does not cover every boss. Cold damage can destroy '
            'corpses. No IAS, socket filler or permanent curse uptime is assumed.',
        ],
    }
