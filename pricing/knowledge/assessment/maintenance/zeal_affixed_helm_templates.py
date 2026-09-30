"""Reviewed Zeal affixed helmet alternatives from the explicit equipment table."""

from inventory_tracking.items.metadata import metadata


MEMBERS = {
    'Rare Circlet': {
        'slug': 'rare-circlet',
        'quality': 'rare',
        'types': ['circ'],
        'core': (('83:3', 2), ('105:0', 20)),
        'stats': ('83:3', '105:0', '225:0', '7:0', '80:0', '93:0', '153:0', '36:0'),
        'role': 'Zeal Paladin skills and casting circlet alternative',
        'conditions': [
            'Two Paladin skills and 20 FCR support the caster side of a Zeal setup. FCR affects casting '
            'such as Teleport, not Zeal attack speed; check the complete casting breakpoint and teleport source.',
            'Visionary attack rating scales with wearer level and is separate from flat attack rating. '
            'Life and magic find add survival and farming utility. Neither FCR nor magic find is melee damage.',
        ],
    },
    'Blood Crafted Armet': {
        'slug': 'blood-helm',
        'quality': 'crafted',
        'types': ['helm'],
        'core': (('225:0', 1), ('60:0', 1), ('141:0', 5), ('7:0', 10)),
        'stats': ('225:0', '60:0', '141:0', '7:0', '16:0', '93:0', '153:0', '36:0'),
        'role': 'Zeal Visionary Blood helm alternative',
        'conditions': [
            'Blood helm crafting supplies 1-3% life leech, 10-20 life and 5-10% Deadly Strike. '
            'Visionary is a separate affix for level-scaled attack rating. Additional life and enhanced '
            'defense are optional affixes, not guaranteed craft properties.',
            'Deadly Strike supports eligible physical attacks; it is not Crushing Blow. Leech needs '
            'physical damage against drainable targets and does not replace Life Tap against Ubers.',
        ],
    },
}


def expand_zeal_affixed_helm(row):
    member = MEMBERS[row['item']]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'player', 'Helmets'):
        raise ValueError('Unreviewed affixed helm context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in (0, 1, 2)]},
        *({'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True} for key, value in member['core']),
    ]
    if member['quality'] == 'crafted':
        codes = [b['code'] for b in metadata()['bases'].values() if b['name'] in ('Helm', 'Casque', 'Armet')]
        if len(codes) != 3:
            raise ValueError('Missing native Blood helm family')
        must.append({'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in codes]})
    return {
        **{k: v for k, v in row.items() if k not in ('item', 'class')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'types': member['types'],
        'qualities': [member['quality']],
        'must': {'all': must},
        'important_stats': list(member['stats']),
        'preferences': [
            {
                'label': 'Two sockets for the linked Cham/Ber setup',
                'when': {'op': 'fact_eq', 'field': 'sockets', 'value': 2},
            }
        ],
        'conditions': member['conditions']
        + [
            'The linked example has two sockets filled with Cham and Ber. Fewer sockets remain preparation '
            'candidates but cannot fit that exact example. Cannot Be Frozen and physical reduction must '
            'be observed; neither is inferred from the base or a free socket. Check equipment requirements '
            'and the complete loadout before replacing a conventional unique or set helmet.',
        ],
    }
