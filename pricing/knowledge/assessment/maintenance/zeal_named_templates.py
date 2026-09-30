"""Named Zeal alternatives with explicit preparation and durability requirements."""

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    "Tal Rasha's Horadric Crest": {
        'quality': 'set',
        'slot': 'Helmets',
        'role': 'Zeal dual-leech and resistance helmet alternative',
        'stats': ('60:0', '62:0', '7:0', '9:0', '39:0', '41:0', '43:0', '45:0', '93:0'),
        'desirable': ('60:0', '62:0', '39:0', '41:0', '43:0', '45:0', '93:0'),
        'conditions': [
            'Standalone life and mana leech support eligible physical Zeal hits. Difficulty and target '
            'drain effectiveness reduce leech; it is not Life Tap or guaranteed healing against Ubers.',
            'Life, mana and all resistances apply to the player. This helmet gives no native IAS, '
            'Crushing Blow or Paladin skills. The linked example uses a 15 IAS jewel; only observed '
            'socket bonuses count, and the full weapon setup determines attack-speed breakpoints.',
            'Original and upgraded bases are recognized; compare equipment requirements before upgrading. '
            'Set items are nonethereal. Other Tal pieces and full-set bonuses are not assumed.',
        ],
    },
    'Rune Master': {
        'slot': 'Weapon',
        'role': 'Ethereal Zeal customizable weapon alternative',
        'stats': ('17:0', '18:0', '44:0', '153:0', '93:0', '141:0'),
        'desirable': ('17:0', '18:0', '93:0', '141:0'),
        'conditions': [
            'The guide explicitly names the ethereal weapon. Sustainable player attacks require Zod. '
            'The linked five-socket example uses Zod, two Lo runes and two damage/IAS jewels; their '
            'bonuses must come from the observed contents, not the unique identity.',
            'Five sockets leave four customization slots after Zod. Three or four sockets are usable '
            'candidates but cannot fit that complete example. Check weapon speed, Fanaticism and all IAS; '
            'the base unique supplies no IAS, leech or Crushing Blow.',
        ],
    },
    'Herald of Zakarum': {
        'slot': 'Off-Hand',
        'role': 'Zeal Paladin skills and blocking shield alternative',
        'stats': (
            '83:3',
            '188:24',
            '16:0',
            '102:0',
            '20:0',
            '0:0',
            '3:0',
            '119:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '17:0',
            '18:0',
            '93:0',
        ),
        'desirable': ('83:3', '188:24', '20:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': [
            'Paladin skills support Zeal and Fanaticism; Combat ranks support Zeal but not Fanaticism. '
            'Player Vitality supplies life, while block chance also needs Dexterity and character level.',
            'The linked example is upgraded with a damage/IAS jewel. Original and upgraded bases are '
            "recognized; upgrading changes defense, requirements and Smite damage, not the main weapon's "
            'Zeal damage. Ethereal use requires observed Indestructible and uses the socket for Zod instead.',
        ],
    },
    'Stormshield': {
        'slot': 'Off-Hand',
        'role': 'Zeal physical reduction and blocking shield alternative',
        'stats': ('214:0', '36:0', '0:0', '102:0', '41:0', '20:0', '43:0', '17:0', '18:0', '93:0'),
        'desirable': ('36:0', '20:0', '102:0'),
        'conditions': [
            'Physical damage reduction and blocking provide different protection; neither proves maximum '
            'block or resistance coverage. Defense scales with level. Fire and poison resistance need other gear.',
            'Native Indestructible does not make Stormshield an ethereal drop. The linked damage/IAS jewel '
            'is a socket choice, not an intrinsic unique bonus; full attack speed depends on the weapon setup.',
        ],
    },
    "Skullder's Ire": {
        'slot': 'Body Armors',
        'role': 'Zeal level-scaled magic-find armor alternative',
        'stats': ('127:0', '240:0', '16:0', '35:0', '252:0', '39:0', '41:0', '43:0', '45:0'),
        'desirable': ('127:0', '240:0'),
        'conditions': [
            'Magic find scales with character level; it changes eligible loot quality, not guaranteed drop '
            'value. The armor supplies no IAS, physical reduction or native resistance. The guide example '
            'uses Um for resistance; no filler is assumed.',
            'Observed self-repair supports ethereal player use; check repair pace and base requirements. '
            'Original and upgraded armor bases are recognized. Magic damage reduction is not percentage '
            'physical reduction.',
        ],
    },
}


def expand_zeal_named(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['build'] != 'zeal-paladin'
        or row['class'] != 'Paladin'
        or row['side'] != 'player'
        or row['slot'] != MEMBERS[name]['slot']
    ):
        raise ValueError('Unreviewed named Zeal use')
    member = MEMBERS[name]
    quality = member.get('quality', 'unique')
    noneth = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = noneth
    if name == 'Rune Master':
        durability = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
    elif name in ('Herald of Zakarum', "Skullder's Ire"):
        key = '152:0' if name == 'Herald of Zakarum' else '252:0'
        durability = {
            'any': [
                noneth,
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                        {'op': 'stat_at_least', 'key': key, 'value': 1, 'absent_is_zero': True},
                    ]
                },
            ]
        }
    sockets = (3, 4, 5) if name == 'Rune Master' else (0, 1)
    return {
        **{k: v for k, v in row.items() if k not in ('item', 'class', 'template')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [catalog().named[quality, name]['base_definition']['type']],
        'qualities': [quality],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
                {'op': 'fact_eq', 'field': 'identified', 'value': True},
                named_base_condition(name, quality),
                durability,
                {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in sockets]},
            ]
        },
        **(
            {
                'required_socket_item': 'Zod Rune',
                'preferences': [
                    {
                        'label': 'Five sockets for the full linked customization',
                        'when': {'op': 'fact_eq', 'field': 'sockets', 'value': 5},
                    }
                ],
            }
            if name == 'Rune Master'
            else {}
        ),
        'important_stats': list(member['stats']),
        'conditions': member['conditions'],
    }
