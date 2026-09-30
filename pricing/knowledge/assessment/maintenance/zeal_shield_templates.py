"""Source-reviewed Zeal shields; physical offense and defensive recipes stay distinct."""

from pricing.knowledge.assessment.maintenance.aura_recipe_templates import recipe_condition


RESISTANCES = ('39:0', '41:0', '43:0', '45:0')
MEMBERS = {
    'Phoenix': {
        'role': 'Zeal physical damage and Redemption shield alternative',
        'stats': ('17:0', '18:0', '151:124', '143:0', '32:0', '40:0', '42:0', '7:0'),
        'desirable': ('17:0', '18:0', '151:124'),
        'conditions': [
            'Shield Enhanced Damage contributes off-weapon physical damage to Zeal; it is not weapon-base '
            'damage or a multiplier to all elemental damage. Compare the full physical damage setup.',
            'Redemption requires usable corpses and is not guaranteed boss sustain. Fire resistance '
            "piercing benefits only the wielder's fire damage, not physical Zeal or allied attacks. "
            'Firestorm and level-up Blaze procs are not assumed active.',
        ],
    },
    'Exile': {
        'role': 'Zeal self-repairing Defiance and Life Tap shield alternative',
        'stats': ('151:104', '188:25', '102:0', '16:0', '252:0', '198:5253', '40:0', '44:0', '80:0', '74:0'),
        'desirable': ('151:104', '16:0', '198:5253'),
        'conditions': [
            'Offensive Auras ranks support Fanaticism, not Zeal Combat Skills. Defiance is a separate '
            'equipped aura; defense depends on base defense and the complete setup.',
            'Life Tap requires a successful on-striking proc; owning Exile does not prove the curse is '
            'active. Ethereal use requires observed self-repair; check repair pace against durability loss.',
        ],
    },
    'Sanctuary': {
        'role': 'Zeal resistance and blocking shield alternative',
        'stats': ('102:0', '20:0', '99:0', '16:0', '32:0', '2:0', '35:0'),
        'desirable': (*RESISTANCES, '99:0', '20:0'),
        'conditions': [
            'The 50\u201370 recipe resistance roll is separate from inherent Paladin shield resistance. '
            'Recovery, faster blocking, Dexterity and defense provide different survival benefits.',
            'Slow Missiles charges require deliberate use and remaining charges; the effect is not '
            'assumed active. This recipe supplies no Cannot Be Frozen.',
        ],
    },
    'Rhyme': {
        'role': 'Zeal Cannot Be Frozen and magic-find shield alternative',
        'stats': ('153:0', '102:0', '20:0', '80:0', '79:0', '27:0'),
        'desirable': ('153:0', *RESISTANCES, '80:0'),
        'conditions': [
            'Cannot Be Frozen protects attacks from ordinary cold chill; it does not remove every slow '
            'effect. Shield Shael adds to recipe FBR for 40 total; this is not attack speed.',
            'Recipe resistance and native Paladin shield resistance add separately. Magic find affects '
            'eligible drops, not the damage or guaranteed value of a drop.',
        ],
    },
}


def expand_zeal_shield(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['build'] != 'zeal-paladin'
        or row['class'] != 'Paladin'
        or row['side'] != 'player'
        or row['slot'] != 'Off-Hand'
    ):
        raise ValueError('Unreviewed Zeal shield use')
    member = MEMBERS[name]
    types = ['ashd'] if name == 'Exile' else ['shie', 'ashd']
    noneth = {'op': 'fact_eq', 'field': 'ethereal', 'value': False}
    durability = noneth
    if name == 'Exile':
        durability = {
            'any': [
                noneth,
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'ethereal', 'value': True},
                        {'op': 'stat_at_least', 'key': '252:0', 'value': 1, 'absent_is_zero': True},
                    ]
                },
            ]
        }
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
                durability,
            ]
        },
        'important_stats': [*member['stats'], *RESISTANCES],
        'conditions': [
            *member['conditions'],
            'Only the active shield set supplies these benefits. Blocking depends on base, Dexterity, '
            'character level and stance; no maximum block is inferred. Native resistance or damage/AR '
            'automods are separate from recipe rolls. The guide does not mandate a particular base.',
        ],
    }
