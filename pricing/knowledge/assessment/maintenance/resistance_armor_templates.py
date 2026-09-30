"""Reviewed early mercenary armor with four independently linked resistance runes."""

from inventory_tracking.items.metadata import metadata


MEMBERS = {
    'lightning-fury-amazon-guide': ('Amazon', ('Act 2 Might', 'Act 2 Holy Freeze')),
    'lightning-strike-amazon': ('Amazon', ('Act 2 Holy Freeze',)),
    'double-throw-barbarian-guide': ('Barbarian', ('Act 2 Might', 'Act 5 Frenzy')),
    'poison-nova-necromancer': ('Necromancer', ('Act 2 Might',)),
    'summoner-necromancer-guide': ('Necromancer', ('Act 2 Might',)),
    'berserk-barbarian': ('Barbarian', ('Act 2 Might',)),
    'fissure-druid': ('Druid', ('Act 2 Might', 'Act 5 Bash', 'Act 5 Frenzy')),
    'enchant-sorceress': ('Sorceress', ('Act 2 Prayer',)),
    'lightning-sorceress': ('Sorceress', ('Act 2 Might', 'Act 2 Holy Freeze')),
    'dream-paladin': ('Paladin', ('Act 2 Might',)),
}
RUNES = ('Ral Rune', 'Ort Rune', 'Thul Rune', 'Tal Rune')
RESISTANCES = ('39:0', '41:0', '43:0', '45:0')


def expand_resistance_armor(row):
    member = MEMBERS.get(row['build'])
    if not member or row.get('class') != member[0] or row['side'] != 'merc' or row['slot'] != 'Body Armor':
        raise ValueError('Unreviewed resistance-rune armor membership')
    base = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Dusk Shroud')
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'class')},
        'role': 'Early mercenary resistance-rune armor',
        'review_status': 'reviewed_candidate_rule',
        'types': ['tors'],
        'base_codes': [base],
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': member[0]},
                {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': m} for m in member[1]]},
                *[
                    {'op': 'fact_eq', 'field': key, 'value': value}
                    for key, value in (
                        ('identified', True),
                        ('base_code', base),
                        ('name', 'Dusk Shroud'),
                        ('sockets', 4),
                        ('socket_contents', 'filled'),
                    )
                ],
                {'op': 'socket_runes_equal', 'value': list(RUNES)},
                *[{'op': 'stat_at_least', 'key': key, 'value': 30, 'absent_is_zero': True} for key in RESISTANCES],
            ]
        },
        'important_stats': list(RESISTANCES),
        'ethereal_preference': {'preference': 'preferred', 'reason': 'Mercenary armor does not lose durability.'},
        'conditions': [
            'Four linked Ral, Ort, Thul and Tal runes supply 30% fire, lightning, cold and poison resistance. '
            'This is a socketed armor setup, not a runeword. It supplies no life leech or damage reduction.',
            'Meet the Dusk Shroud level and Strength requirements; Early-Game is the guide gear tier, not '
            'a promise of low-level usability. Compare actual defense and total resistances after penalties. '
            'Ethereal improves mercenary armor defense but is not mandatory; unknown ethereal status is not a premium.',
            'Filled sockets cannot hold a runeword until emptied; removing the contents destroys the runes. '
            'The player four-Topaz Magic Find setup is a separate use of this base.',
        ],
    }
