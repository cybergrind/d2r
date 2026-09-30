"""Reviewed Zeal inventory charm affix combinations, including native low rolls."""

from inventory_tracking.items.metadata import metadata


MEMBERS = {
    'Sharp Grand Charm of Maiming': ('grand-sharp-maiming', 'lcha', (('19:0', 49), ('22:0', 10))),
    'Resistance Small Charm': ('small-resistance', 'scha', (('39:0', 10), ('41:0', 10), ('43:0', 10), ('45:0', 10))),
    'Resistance Grand Charm': ('grand-resistance', 'lcha', (('39:0', 26), ('41:0', 26), ('43:0', 26), ('45:0', 26))),
    'Sharp Grand Charm of Vita': ('grand-sharp-vita', 'lcha', (('19:0', 49), ('22:0', 7), ('7:0', 36))),
    'Steel Grand Charm of Vita': ('grand-steel-vita', 'lcha', (('19:0', 88), ('7:0', 36))),
    'Sharp Grand Charm of Balance': ('grand-sharp-balance', 'lcha', (('19:0', 49), ('22:0', 7), ('99:0', 12))),
    'Steel Grand Charm of Balance': ('grand-steel-balance', 'lcha', (('19:0', 88), ('99:0', 12))),
    'Sharp Grand Charm': ('grand-sharp', 'lcha', (('19:0', 49), ('22:0', 7))),
    'Steel Grand Charm': ('grand-steel', 'lcha', (('19:0', 88),)),
    'Shimmering Grand Charm of Balance': (
        'grand-shimmering-balance',
        'lcha',
        (('39:0', 13), ('41:0', 13), ('43:0', 13), ('45:0', 13), ('99:0', 12)),
    ),
    'Shimmering Grand Charm': ('grand-shimmering', 'lcha', (('39:0', 13), ('41:0', 13), ('43:0', 13), ('45:0', 13))),
    'Fine Small Charm of Good Luck': ('fine-good-luck', 'scha', (('19:0', 10), ('22:0', 1), ('80:0', 6))),
    'Steel Small Charm of Good Luck': ('steel-good-luck', 'scha', (('19:0', 25), ('80:0', 6))),
    'Fine Small Charm of Vita': ('fine-vita', 'scha', (('19:0', 10), ('22:0', 1), ('7:0', 16))),
    'Fine Small Charm of Balance': ('fine-balance', 'scha', (('19:0', 10), ('22:0', 1), ('99:0', 5))),
    'Shimmering Small Charm of Good Luck': (
        'shimmering-good-luck',
        'scha',
        (('39:0', 3), ('41:0', 3), ('43:0', 3), ('45:0', 3), ('80:0', 6)),
    ),
    'Shimmering Small Charm of Vita': (
        'shimmering-vita',
        'scha',
        (('39:0', 3), ('41:0', 3), ('43:0', 3), ('45:0', 3), ('7:0', 16)),
    ),
    'Fine Small Charm': ('fine', 'scha', (('19:0', 10), ('22:0', 1))),
    'Small Charm of Good Luck': ('good-luck', 'scha', (('80:0', 6),)),
    'Small Charm of Vita': ('vita', 'scha', (('7:0', 16),)),
    'Shimmering Small Charm': ('shimmering', 'scha', (('39:0', 3), ('41:0', 3), ('43:0', 3), ('45:0', 3))),
    'Sharp Large Charm of Vita': ('sharp-large-vita', 'mcha', (('19:0', 21), ('22:0', 4), ('7:0', 26))),
}


def expand_zeal_charm(row):
    _, kind, core = MEMBERS[row['item']]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'player', 'Charms'):
        raise ValueError('Unreviewed Zeal charm context')
    keys = {key for key, _ in core}
    single_resistance = row['item'].startswith('Resistance ')
    conditions = [
        'Keep in the active inventory for bonuses. Native low rolls within the linked affix tiers qualify; '
        'the perfect planner example is a preference, not a requirement. Compare benefit per inventory cell '
        'and character requirements.'
    ]
    if keys & {'19:0', '22:0'}:
        conditions.append(
            'Attack rating supports hit chance, not guaranteed hits; maximum damage supports physical Zeal '
            'attacks. Evaluate damage and attack rating together with the complete weapon and aura setup.'
        )
    if single_resistance:
        conditions.append(
            'Any one of fire, lightning, cold or poison resistance at the reviewed affix tier qualifies. '
            'Do not add different elements together. Choose the element needed by the full loadout; '
            'this is not an all-resistance charm or proof of a trade premium.'
        )
    elif keys & {'39:0', '41:0', '43:0', '45:0'}:
        conditions.append(
            'All four observed resistances support this Shimmering configuration. Prioritize the actual full- '
            'loadout resistance deficit; additional resistance above the cap needs a specific use.'
        )
    if '99:0' in keys:
        fhr_label = 'Five' if kind == 'scha' else 'Twelve'
        conditions.append(
            f'{fhr_label} FHR helps only in the context of the complete hit-recovery breakpoint; it is not increased '
            'attack speed.'
        )
    if '7:0' in keys:
        conditions.append('Life improves survivability; compare the total life and other bonuses per inventory cell.')
    if '80:0' in keys:
        conditions.append('Magic find supports farming, not damage; balance it against kill speed and survival.')
    requirements = [{'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True} for key, value in core]
    if row['item'] == 'Sharp Grand Charm of Maiming':
        for table, record in (('prefix', '253'), ('suffix', '678')):
            ident = next(
                int(key)
                for key, entry in metadata()['affixes'][table].items()
                if entry['source']['record_key'] == record
            )
            requirements.append({'op': 'affix_present', 'table': table, 'value': ident})
        conditions.append(
            'Requires captured Sharp and Maiming affix IDs. Their maximum-damage contributions roll '
            '7-10 and 3-4, totaling 10-14; a total of 10 alone cannot distinguish plain Sharp.'
        )
    if single_resistance:
        requirements = [{'any': requirements}]
    return {
        **{key: value for key, value in row.items() if key not in ('item', 'class')},
        'role': 'Zeal inventory: ' + row['item'],
        'review_status': 'reviewed_candidate_rule',
        'types': [kind],
        'qualities': ['magic'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
                {'op': 'fact_eq', 'field': 'identified', 'value': True},
                {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
                {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
                {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
                *requirements,
            ]
        },
        'important_stats': [key for key, _ in core],
        'conditions': conditions,
    }
