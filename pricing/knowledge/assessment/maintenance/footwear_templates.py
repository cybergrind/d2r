"""Reviewed standalone boot benefits; loadout caps and set bonuses stay separate."""

from inventory_tracking.items.stat_constants import CLASS_NAMES


MEMBERS = {
    "Aldur's Advance": {
        'quality': 'set',
        'important_stats': ['96:0', '7:0', '39:0'],
        'desirable': ['96:0', '39:0'],
        'conditions': [
            'Individual boots supply movement, life and fire resistance; '
            'other Aldur set bonuses require actual companion pieces.'
        ],
    },
    'Waterwalk': {
        'quality': 'unique',
        'important_stats': ['96:0', '7:0', '2:0', '40:0'],
        'desirable': ['7:0', '40:0'],
        'conditions': [
            'Maximum fire resistance raises the cap; it does not supply the resistance needed to reach that cap. '
            'Dexterity is supporting utility, not proof of maximum block.'
        ],
    },
    'Sandstorm Trek': {
        'quality': 'unique',
        'important_stats': ['96:0', '99:0', '0:0', '3:0', '45:0'],
        'desirable': ['99:0', '45:0'],
        'conditions': [
            'Recovery breakpoints and poison resistance depend on the full loadout. '
            'Ethereal use requires functioning self-repair; allow durability to recover.'
        ],
    },
}


def expand_footwear(row):
    name = row['item']
    if name not in MEMBERS or row['class'] not in CLASS_NAMES or row['side'] != 'player' or row['slot'] != 'Boots':
        raise ValueError('Invalid player footwear template membership')
    member = MEMBERS[name]
    nonethereal = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = nonethereal
    if name == 'Sandstorm Trek':
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
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': 'Player movement and defensive boot alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': ['boot'],
        'qualities': [member['quality']],
        'important_stats': list(member['important_stats']),
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
                {'op': 'fact_eq', 'field': 'identified', 'value': True},
                {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
                durability,
            ]
        },
        'conditions': [
            'Check wearer requirements and complete loadout needs. Native minimum rolls retain utility; '
            'the guide listing does not establish a price or best-in-slot claim.',
            *member['conditions'],
            *row.get('conditions', []),
        ],
    }
