"""Reviewed early-game mercenary recipes and exact resistance-filled equipment."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.aura_recipe_templates import recipe_condition
from pricing.knowledge.assessment.maintenance.native_membership import unique_base_condition


RESISTANCES = ('39:0', '41:0', '43:0', '45:0')
MEMBERS = {
    'Hustle (armor)': {
        'slug': 'hustle',
        'slot': 'Body Armor',
        'types': ['tors'],
        'stats': ('93:0', '96:0', '99:0', '2:0', *RESISTANCES),
        'conditions': [
            'Armor IAS, movement, recovery, Dexterity and resistance support the mercenary. '
            'Evade is not credited as a mercenary skill. No weapon Fanaticism or Burst of Speed '
            'effect belongs to this armor recipe. Full attack speed depends on the weapon and other gear.'
        ],
    },
    'Bulwark': {
        'slug': 'bulwark',
        'slot': 'Helmet',
        'types': ['helm', 'circ'],
        'stats': ('60:0', '36:0', '34:0', '99:0', '74:0', '16:0', '76:0'),
        'conditions': [
            'Life leech requires eligible physical hits and drainable targets. Flat and percentage '
            'physical reduction are separate; elemental resistance needs other gear. '
            'Item Vitality does not increase mercenary life.'
        ],
    },
    'Undead Crown': {
        'slug': 'undead-crown',
        'slot': 'Helmet',
        'types': ['helm'],
        'stats': ('60:0', '45:0', '118:0', '16:0', '122:0', '124:0'),
        'conditions': [
            'Leech needs eligible physical hits. Damage and attack rating against undead are '
            'target-specific; poison resistance does not protect against other elements. '
            'Half Freeze Duration is not Cannot Be Frozen. Skeleton Mastery is not a mercenary benefit.'
        ],
    },
    'Gemmed Dusk Shroud': {
        'slug': 'resistance-armor',
        'slot': 'Body Armor',
        'types': ['tors'],
        'base': 'Dusk Shroud',
        'runes': ('Ral Rune', 'Ort Rune', 'Thul Rune', 'Tal Rune'),
        'stats': RESISTANCES,
        'conditions': [
            'The linked four-socket armor contains Ral, Ort, Thul and Tal for 30 resistance to '
            'each element. This is resistance-filled equipment, not a completed runeword. '
            'An empty socket or different filler does not satisfy this setup.'
        ],
    },
    'Gemmed Mask': {
        'slug': 'resistance-mask',
        'slot': 'Helmet',
        'types': ['helm'],
        'base': 'Mask',
        'runes': ('Ral Rune', 'Ort Rune', 'Tal Rune'),
        'stats': ('39:0', '41:0', '45:0'),
        'conditions': [
            'The linked three-socket mask contains Ral, Ort and Tal for 30 fire, lightning and '
            'poison resistance. It supplies no cold resistance or life leech. '
            'Verify actual fillers; this is not a completed runeword.'
        ],
    },
}


def expand_zeal_merc_equipment(row):
    name = row['item']
    member = MEMBERS[name]
    if (row['build'], row['class'], row['side'], row['slot']) != (
        'zeal-paladin',
        'Paladin',
        'merc',
        member['slot'],
    ):
        raise ValueError('Unreviewed early Zeal mercenary equipment context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {
            'any': [
                {'op': 'context_eq', 'field': 'mercenary_type', 'value': value}
                for value in ('Act 2 Might', 'Act 5 Frenzy')
            ]
        },
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
    ]
    if name == 'Undead Crown':
        must += [
            unique_base_condition(name),
            {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': count} for count in (0, 1)]},
        ]
    elif 'runes' in member:
        base = next(base for base in metadata()['bases'].values() if base['name'] == member['base'])
        must += [
            {'op': 'fact_eq', 'field': 'base_code', 'value': base['code']},
            {'op': 'fact_eq', 'field': 'sockets', 'value': len(member['runes'])},
            {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
            {'op': 'socket_runes_equal', 'value': list(member['runes'])},
            *[{'op': 'stat_at_least', 'key': key, 'value': 30, 'absent_is_zero': True} for key in member['stats']],
        ]
    else:
        must.append(recipe_condition(name, member['types']))
    return {
        **{key: value for key, value in row.items() if key not in ('item', 'class')},
        'role': 'Early mercenary equipment: ' + name,
        'review_status': 'reviewed_candidate_rule',
        **({'names': [name]} if 'runes' not in member else {}),
        **({'base_codes': [base['code']]} if 'runes' in member else {}),
        'types': member['types'],
        'qualities': ['unique'] if name == 'Undead Crown' else ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': list(member['stats']),
        'preferences': [
            {
                'label': 'Ethereal mercenary equipment has no durability loss',
                'when': {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
            }
        ],
        'conditions': [
            *member['conditions'],
            'Reviewed for the early-game Act 2 Might or Act 5 Frenzy table branch. '
            'Verify level and equipment requirements; one piece does not establish a complete setup. '
            'Assess existing completed items separately from current Non-Ladder recipe creation.',
        ],
    }
