"""Named socket components; recipient ownership never follows from a loose jewel."""

from pricing.knowledge.definition_store import catalog


# Damage type and native damage/pierce selectors are independent of guide typography.
ELEMENTS = {
    'fire': ('329:0', '333:0'),
    'lightning': ('330:0', '334:0'),
    'cold': ('331:0', '335:0'),
    'poison': ('332:0', '336:0'),
    'magic': ('357:0', '358:0'),
    'physical': ('17:0', '18:0', '366:0'),
}
COLOSSAL = {
    "Defender's Fire": 'fire',
    "Defender's Bile": 'poison',
    "Guardian's Light": 'magic',
    "Guardian's Thunder": 'lightning',
    "Protector's Frost": 'cold',
    "Protector's Stone": 'physical',
}
BUILDS = {
    'abyss-warlock-build-guide': ('Warlock', ('magic',)),
    'berserk-barbarian': ('Barbarian', ('magic',)),
    'blessed-hammer-paladin': ('Paladin', ('magic',)),
    'blizzard-sorceress': ('Sorceress', ('cold',)),
    'double-throw-barbarian-guide': ('Barbarian', ('physical',)),
    'echoing-strike-warlock-guide': ('Warlock', ('magic',)),
    'enchant-sorceress': ('Sorceress', ('fire',)),
    'fire-warlock-guide': ('Warlock', ('fire',)),
    'fissure-druid': ('Druid', ('fire',)),
    'fist-of-the-heavens-paladin': ('Paladin', ('magic', 'lightning')),
    'gold-find-barbarian': ('Barbarian', ('physical',)),
    'lightning-fury-amazon-guide': ('Amazon', ('lightning',)),
    'lightning-sentry-assassin': ('Assassin', ('lightning',)),
    'lightning-sorceress': ('Sorceress', ('lightning',)),
    'lightning-strike-amazon': ('Amazon', ('lightning',)),
    'meteor-sorceress': ('Sorceress', ('fire',)),
    'mirrored-blades-warlock-guide': ('Warlock', ('physical',)),
    'nova-sorceress-guide': ('Sorceress', ('lightning',)),
    'poison-nova-necromancer': ('Necromancer', ('poison',)),
    'smite-paladin': ('Paladin', ('physical',)),
    'strafe-amazon': ('Amazon', ('physical',)),
    'summoner-necromancer-guide': ('Necromancer', ('physical',)),
}


def expand_named_jewel(row):
    name, build, host = row['item'], row['build'], row['host']
    klass, elements = BUILDS[build]
    if name not in COLOSSAL and name != 'Rainbow Facet':
        raise ValueError('Unreviewed jewel')
    element = COLOSSAL.get(name, row.get('element'))
    if (
        row['class'] != klass
        or element not in elements
        or row['side'] != 'player'
        or row['slot'] not in ('Helmet', 'Weapon', 'Off-Hand', 'Body Armor')
    ):
        raise ValueError('Unreviewed jewel damage/recipient context')
    if not any((q, host) in catalog().named for q in ('unique', 'set')):
        raise ValueError('Unverified named recipient')
    if name == 'Rainbow Facet' and element not in ('fire', 'lightning', 'cold', 'poison'):
        raise ValueError('Unsupported facet element')
    definition = catalog().named['unique', name]
    core = ELEMENTS[element]
    stats = list(core)
    conditions = [
        f'Socket into the cited {host} on the player; the recipient needs an available socket and the '
        'jewel level requirement must be met. A loose jewel grants no inventory bonus. This review '
        'does not establish recipient ownership, its other affixes, or a ready-to-socket full loadout.',
    ]
    if name in COLOSSAL:
        stats.extend(('85:0', '80:0', '79:0'))
        conditions.append(
            'Only one Colossal Jewel can be equipped per character. Treat this as a choice '
            'or replacement for the existing one, not an additional stack. The when-struck '
            'proc is not credited as a permanent buff or ordinary attack damage.'
        )
    else:
        conditions.append(
            'Require the matching elemental damage and resistance-reduction pair. Other '
            'Facet elements do not substitute. Death and level-up triggers do not add '
            'ordinary combat uptime; this use does not select a market-priced trigger variant.'
        )
    if build == 'berserk-barbarian':
        stats.remove('357:0')
        conditions.append(
            'Magic pierce supports converted Berserk damage. No unverified Magic Skill '
            'Damage multiplier for Berserk is credited.'
        )
    if build == 'summoner-necromancer-guide':
        stats = [k for k in stats if k not in ('17:0', '18:0', '366:0')]
        conditions.append(
            'This Summoner component review credits Find and experience utility. Player jewel attack '
            'bonuses do not transfer to skeletons, and ED does not multiply Corpse Explosion. '
            'The physical-pierce interaction with Corpse Explosion needs separate mechanics verification.'
        )
    if build == 'echoing-strike-warlock-guide':
        conditions.append(
            'Magic damage and magic pierce concern Hex Purge; they do not multiply the physical Echoing Strike hit.'
        )
    if build == 'fist-of-the-heavens-paladin':
        conditions.append(
            'Lightning modifiers affect the initial FoH lightning strike, not its magic '
            'Holy Bolts. Magic modifiers concern Holy Bolt/Hammer damage in the Tri-Brid setup.'
        )
    if build == 'smite-paladin':
        if row['slot'] not in ('Helmet', 'Off-Hand'):
            raise ValueError('Smite jewel review requires off-weapon ED')
        conditions.append(
            'Off-weapon ED and physical pierce support Smite. Flat minimum/maximum weapon '
            'damage is not the Grief-style Damage bonus and is not credited to Smite.'
        )
    if build == 'gold-find-barbarian':
        conditions.append(
            'ED supports weapon damage before any Berserk conversion; physical pierce '
            'applies only to physical attacks, not converted magic damage. Find bonuses are '
            'separate from mercenary damage or the War Cry caster variant.'
        )
        if row['variant'] == 'Standard':
            stats.remove('366:0')
    conditions.append(
        'Elemental modifiers apply to the wearer matching damage, not every party member '
        'or mercenary. Check mastery, immunity and other resistance-reduction sources separately.'
    )
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class', 'host', 'element')},
        'role': f'{element.capitalize()} socket jewel for {host}',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': klass},
                *[
                    {'op': 'fact_eq', 'field': k, 'value': v}
                    for k, v in (
                        ('identified', True),
                        ('base_code', definition['base_code']),
                        ('ethereal', False),
                        ('sockets', 0),
                        ('socket_contents', 'empty'),
                    )
                ],
                *[{'op': 'stat_at_least', 'key': k, 'value': 1, 'absent_is_zero': True} for k in core],
            ]
        },
        'depends_on': [
            {
                'label': f'{host} on the intended player recipient',
                'when': {'op': 'context_contains', 'field': 'player_items', 'value': host},
            }
        ],
        'important_stats': stats,
        'conditions': conditions,
    }
