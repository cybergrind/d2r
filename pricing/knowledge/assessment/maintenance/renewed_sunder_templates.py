"""Renewed Sunder uses: fixed native core and observed rolls, never invented affix bounds."""

from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Renewed Black Cleft': (
        '193:0',
        '37:0',
        '358:0',
        'magic',
        {
            'abyss-warlock-build-guide': 'Warlock',
            'berserk-barbarian': 'Barbarian',
            'blessed-hammer-paladin': 'Paladin',
            'echoing-strike-warlock-guide': 'Warlock',
        },
    ),
    'Renewed Bone Break': (
        '192:0',
        '36:0',
        '366:0',
        'physical',
        {
            'double-throw-barbarian-guide': 'Barbarian',
            'echoing-strike-warlock-guide': 'Warlock',
        },
    ),
    'Renewed Cold Rupture': ('187:0', '43:0', '335:0', 'cold', {'blizzard-sorceress': 'Sorceress'}),
    'Renewed Crack of the Heavens': (
        '190:0',
        '41:0',
        '334:0',
        'lightning',
        {
            'dream-paladin': 'Paladin',
            'lightning-fury-amazon-guide': 'Amazon',
            'nova-sorceress-guide': 'Sorceress',
        },
    ),
    'Renewed Flame Rift': (
        '189:0',
        '39:0',
        '333:0',
        'fire',
        {
            'enchant-sorceress': 'Sorceress',
            'fire-blast-assassin': 'Assassin',
        },
    ),
}


def expand_renewed_sunder(row):
    name = row['item']
    immunity, penalty, pierce, damage, builds = MEMBERS[name]
    if (
        builds.get(row['build']) != row['class']
        or row['side'] != 'player'
        or row['slot'] not in ('Charms', 'Unique Charms')
    ):
        raise ValueError('Unreviewed Renewed Sunder use')
    d = catalog().named['unique', name]
    stats = [
        immunity,
        penalty,
        pierce,
        '99:0',
        '96:0',
        '7:0',
        '9:0',
        '35:0',
        '34:0',
        '80:0',
        '0:0',
        '1:0',
        '2:0',
        '3:0',
    ]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': f'Renewed {damage}-sunder inventory alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [d['base_definition']['type']],
        'qualities': ['unique'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
                *[
                    {'op': 'fact_eq', 'field': k, 'value': v}
                    for k, v in (
                        ('identified', True),
                        ('base_code', d['base_code']),
                        ('ethereal', False),
                        ('sockets', 0),
                        ('socket_contents', 'empty'),
                    )
                ],
                {'op': 'stat_at_least', 'key': immunity, 'value': 300, 'absent_is_zero': True},
                {'not': {'op': 'stat_at_least', 'key': immunity, 'value': 301}},
            ]
        },
        'important_stats': stats,
        'conditions': [
            f'Keep in active inventory and meet level {d["game_definition"]["lvl req"]}. This is the Renewed '
            f'identity on the Crafted Sunder Charm base, not an original or Latent charm. It breaks matching '
            f'{damage} immunity only; follow-up resistance reduction and survival depend on the full setup.',
            'The native wearer penalty is a cost. Rolled recovery, movement, life/mana, mitigation, '
            'attributes and magic find are credited only when observed. The illustrated guide values '
            'are examples, not minimum requirements or verified affix ranges. Generated-affix bounds '
            'and complete market comparisons remain separate gaps; no perfect-roll claim is inferred.',
            *(
                [
                    'For Echoing Strike, this magic-sunder use concerns the Hex Purge magic component, not '
                    'the physical Echoing hit. It requires the actual magic-damage setup.'
                ]
                if name == 'Renewed Black Cleft' and row['build'] == 'echoing-strike-warlock-guide'
                else []
            ),
        ],
    }
