"""Three distinct caster amulet alternatives in the Zeal gear table."""

MEMBERS = {
    'teleport': {
        'span': 154,
        'core': (),
        'stats': ('83:3', '105:0', '9:0', '27:0', 'charge:54', '60:0', '7:0'),
        'role': 'Zeal caster-craft Teleport-charge alternative',
        'conditions': [
            'Use this charged movement alternative only without Enigma. Charges must remain available; '
            'recharge when empty. Teleport charges do not grant a permanent skill or prove any active effect.',
            'Paladin skills support Zeal and auras; FCR speeds casting, not Zeal. Life and leech are useful '
            'additional affixes, not guaranteed caster-craft properties. Leech needs drainable physical hits.',
        ],
    },
    'resistance-mf': {
        'span': 155,
        'core': (('80:0', 21), ('39:0', 16), ('41:0', 16), ('43:0', 16), ('45:0', 16)),
        'stats': ('83:3', '105:0', '9:0', '27:0', '80:0', '39:0', '41:0', '43:0', '45:0'),
        'role': 'Zeal caster-craft resistance and magic-find alternative',
        'conditions': [
            'The reviewed combination adds Prismatic resistance and Felicitous/Fortune magic find. '
            'Native lower rolls give 16 all resistances and 21 MF; the planner shows 20 and 35. '
            'These affixes support survival and farming, not direct melee damage or rune drop quality.',
        ],
    },
    'fast-mf': {
        'span': 156,
        'core': (('105:0', 15), ('80:0', 21)),
        'stats': ('83:3', '105:0', '9:0', '27:0', '80:0'),
        'role': 'Zeal faster-casting and magic-find craft alternative',
        'conditions': [
            'Apprentice adds 10 FCR to the craft roll, giving 15-20 total; 20 is preferred for the '
            'linked setup. Verify the complete casting breakpoint. Magic find supports farming, '
            'and neither FCR nor MF increases Zeal attack damage.',
        ],
    },
}


def expand_zeal_caster_amulet(row):
    member = MEMBERS[row['branch']]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'player', 'Amulets'):
        raise ValueError('Unreviewed caster amulet context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
    ]
    core = {'83:3': 2, '105:0': 5, '9:0': 10, '27:0': 4}
    core.update(member['core'])
    must.extend(
        {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True} for key, value in core.items()
    )
    depends = []
    if row['branch'] == 'teleport':
        must.append({'op': 'charge_skill', 'skill_id': 54, 'value': 0})
        depends = [
            {'label': 'Teleport charges remain available.', 'when': {'op': 'charge_skill', 'skill_id': 54, 'value': 1}},
            {
                'label': 'Use this charge alternative without Enigma.',
                'when': {'not': {'op': 'context_contains', 'field': 'player_items', 'value': 'Enigma'}},
            },
        ]
    return {
        **{k: v for k, v in row.items() if k not in ('branch', 'class')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'types': ['amul'],
        'qualities': ['crafted'],
        'must': {'all': must},
        'depends_on': depends,
        'important_stats': [key for key in member['stats'] if not key.startswith('charge:')],
        'preferences': [
            {
                'label': '20 FCR for the linked faster-casting setup',
                'when': {'op': 'stat_at_least', 'key': '105:0', 'value': 20, 'absent_is_zero': True},
            }
        ]
        if row['branch'] == 'fast-mf'
        else [],
        'conditions': member['conditions']
        + [
            'Caster crafting supplies 5-10 FCR, 10-20 mana and 4-10% mana regeneration. Paladin skills '
            'and the other listed modifiers are additional affixes. Check equipment requirements and '
            'the complete casting setup.',
        ],
    }
