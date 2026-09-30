"""Source-specific Zeal physical gloves and rare survival-belt alternatives."""

from inventory_tracking.items.metadata import metadata


MEMBERS = {
    'Blood Crafted Ring': {
        'slug': 'blood-ring',
        'slot': 'Rings',
        'quality': 'crafted',
        'type': 'ring',
        'core': (('60:0', 8), ('7:0', 41), ('0:0', 1), ('21:0', 6), ('19:0', 101)),
        'stats': ('60:0', '7:0', '0:0', '21:0', '19:0'),
        'role': 'Zeal physical damage and high-leech Blood ring alternative',
        'conditions': [
            'This branch combines the Blood recipe with Lamprey leech, Mammoth life, Excellence minimum '
            'damage and Platinum attack rating. Native lower rolls total 8 leech, 41 life, 1 Strength, '
            '6 minimum damage and 101 attack rating; the linked example has 11/60/5/9/120.',
            'The recipe alone supplies only 1-3 leech, 10-20 life and 1-5 Strength. Extra leech, life, '
            'damage and attack rating require affixes. Leech depends on drainable physical hits and does '
            'not replace Life Tap against Ubers. Attack rating does not guarantee a hit.',
            'Compare the complete ring pair and equipment requirements. This ring supplies no native '
            'Cannot Be Frozen, FCR, mana leech or resistances; other ring combinations have separate uses.',
        ],
    },
    'Blood Crafted Gloves': {
        'slug': 'blood-gloves',
        'slot': 'Gloves',
        'quality': 'crafted',
        'type': 'glov',
        'core': (('93:0', 20), ('60:0', 1), ('136:0', 5), ('7:0', 10)),
        'stats': ('93:0', '60:0', '136:0', '7:0', '0:0', '41:0', '80:0'),
        'bases': ('Heavy Gloves', 'Sharkskin Gloves', 'Vampirebone Gloves'),
        'role': 'Zeal IAS and Crushing Blow Blood gloves alternative',
        'conditions': [
            'Blood gloves supply 1-3% life leech, 10-20 life and 5-10% Crushing Blow; 20 IAS is a separate '
            'affix. Native low craft rolls remain candidates. Strength, lightning resistance and magic find '
            'are additional useful affixes, not guaranteed recipe bonuses.',
            'Check IAS against the complete weapon and Fanaticism setup. Crushing Blow is not Deadly Strike; '
            'leech needs drainable physical hits and does not replace Life Tap against Ubers. Base upgrades '
            'change equipment requirements, not these modifier roles.',
        ],
    },
    'Rare Belt': {
        'slug': 'rare-belt',
        'slot': 'Belts',
        'quality': 'rare',
        'type': 'belt',
        'core': (('99:0', 24), ('0:0', 21), ('7:0', 41), ('39:0', 21), ('41:0', 21), ('43:0', 21)),
        'stats': ('99:0', '0:0', '7:0', '39:0', '41:0', '43:0'),
        'role': 'Zeal hit-recovery and triple-resistance rare belt alternative',
        'conditions': [
            'This branch covers the guide example with Stability FHR, Atlas Strength, Colossus life and '
            'fire/lightning/cold resistance affixes. Minimum rolls within those native affix tiers qualify; '
            'the planner uses perfect 30 Strength, 60 life and 30 of each resistance.',
            'These are survival and equipment-support modifiers, not leech, IAS or physical damage reduction. '
            'Compare full-loadout resistance and FHR breakpoints, belt potion rows and base requirements '
            'before replacing a unique belt. Other rare-belt combinations require separate assessment.',
        ],
    },
}


def expand_zeal_affixed_accessory(row):
    member = MEMBERS[row['item']]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'player', member['slot']):
        raise ValueError('Unreviewed Zeal accessory context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
        *({'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True} for key, value in member['core']),
    ]
    if 'bases' in member:
        codes = [base['code'] for base in metadata()['bases'].values() if base['name'] in member['bases']]
        if len(codes) != len(member['bases']):
            raise ValueError('Missing native Blood glove family')
        must.append({'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in codes]})
    return {
        **{key: value for key, value in row.items() if key not in ('item', 'class')},
        'role': member['role'],
        'review_status': 'reviewed_candidate_rule',
        'types': [member['type']],
        'qualities': [member['quality']],
        'must': {'all': must},
        'important_stats': list(member['stats']),
        'conditions': member['conditions'],
    }
