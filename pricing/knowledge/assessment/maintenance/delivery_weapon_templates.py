"""Named casting, projectile delivery and hybrid alternatives from exact guide variants."""

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Demon Machine': (
        'Sorceress',
        'enchant-sorceress',
        ('Main alternatives',),
        ('156:0', '158:0', '19:0', '9:0', '31:0'),
    ),
    'Kuko Shakaku': ('Sorceress', 'enchant-sorceress', ('Budget',), ('156:0', '158:0', '48:0', '49:0', '93:0')),
    "Butcher's Pupil": ('Paladin', 'zeal-paladin', ('Gear alternatives',), ('17:0', '18:0', '93:0', '141:0', '135:0')),
    'Hand of Blessed Light': (
        'Paladin',
        'fist-of-the-heavens-paladin',
        ('Main alternatives', 'Holy Bolt Support'),
        ('83:3', '107:101', '107:121', '27:0', '31:0'),
    ),
    "Heaven's Light": ('Paladin', 'fist-of-the-heavens-paladin', ('Tri-Brid',), ('83:3', '93:0', '136:0', '194:0')),
}
SUPPORT_JEWEL = {
    'op': 'socket_jewel_matches',
    'count': 1,
    'stats': {'99:0': 7, '39:0': 40, '41:0': 10, '43:0': 10, '45:0': 10, '114:0': 12},
}


def expand_delivery_weapon(row):
    name = row['item']
    if name not in MEMBERS:
        raise ValueError('Unknown delivery weapon')
    klass, build, variants, stats = MEMBERS[name]
    if (
        row['class'] != klass
        or row['build'] != build
        or row['variant'] not in variants
        or row['side'] != 'player'
        or row['slot'] != 'Weapon'
    ):
        raise ValueError('Invalid delivery weapon source context')
    definition = catalog().named['unique', name]
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': klass},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name),
    ]
    if name != 'Hand of Blessed Light':
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
    sockets = (1, 2, 3) if name == "Heaven's Light" else (0, 1)
    must.append({'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in sockets]})
    dependencies = []
    if name == "Butcher's Pupil":
        base = definition['base_definition']['ultracode']
        dependencies.append(
            {
                'label': 'The listed guide configuration uses the upgraded base; check its higher requirements.',
                'when': {'op': 'fact_eq', 'field': 'base_code', 'value': base},
            }
        )
    if name in ('Kuko Shakaku', "Heaven's Light"):
        ias = 20 if name == 'Kuko Shakaku' else 60
        dependencies.append(
            {
                'label': f'Match the source socket preparation: at least {ias}% weapon IAS.',
                'when': {'op': 'stat_at_least', 'key': '93:0', 'value': ias, 'absent_is_zero': True},
            }
        )
    if name == 'Demon Machine':
        role = 'Enchant explosive-bolt and piercing crossbow alternative'
        conditions = [
            'The source uses an upgraded Demon Crossbow. Upgrading physical base damage does not multiply '
            'Enchant fire damage. Explosive bolts and pierce provide delivery; weapon ED and flat physical '
            'maximum damage are not fire-spell multipliers. Check the full attack-speed setup.'
        ]
    elif name == 'Kuko Shakaku':
        role = 'Budget Enchant explosive-arrow bow alternative'
        conditions = [
            'The Budget source sockets Shael for 20% IAS. Equivalent observed weapon IAS satisfies that '
            'preparation without claiming a particular filler. Amazon-only skill bonuses do not grant '
            'Sorceress skill levels. Explosive arrows and pierce deliver Enchant; weapon ED does not '
            'multiply its fire damage.'
        ]
    elif name == "Butcher's Pupil":
        role = 'Upgraded Zeal Deadly Strike and Open Wounds axe alternative'
        conditions = [
            'The source specifies the upgraded Small Crescent. Native indestructibility prevents ordinary '
            'ethereal spawning. Deadly Strike does not multiply with another critical effect into quadruple '
            'damage. Open Wounds and the rest of the attack-speed setup remain separate.'
        ]
    elif name == 'Hand of Blessed Light':
        role = 'Holy Bolt and Fist of the Heavens casting scepter alternative'
        conditions = [
            'Holy Bolt and Fist of the Heavens skill levels support casting, not hard-point synergies. '
            'Weapon damage, attack rating and the on-striking FoH proc do not multiply cast spell damage. '
            'Ethereal is accepted for casting only.'
        ]
        if row['variant'] == 'Holy Bolt Support':
            must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
            dependencies.append(
                {
                    'label': 'One support jewel meets the source FHR, resistance and damage-to-mana thresholds.',
                    'when': SUPPORT_JEWEL,
                }
            )
            stats = (*stats, *SUPPORT_JEWEL['stats'])
            conditions.append(
                'The support variant explicitly uses an ethereal scepter and a compound rare jewel. Different '
                'jewels cannot be combined into one qualifying payload. Damage Taken Goes To Mana is recovery, '
                'not absorption.'
            )
    else:
        role = 'Tri-Brid FoH/Hammer/Smite skill and Crushing Blow scepter alternative'
        conditions = [
            'The guide limits this alternative to Tri-Brid, with two Shael runes giving 60% weapon IAS. '
            'Other fillers may satisfy the same observed IAS without being identified as Shael. Weapon ED '
            'and target-defense reduction do not improve Smite or spell damage. Native socket rolls are 1-3; '
            'the full Smite breakpoint still depends on the setup.'
        ]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': role,
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {'all': must},
        'depends_on': dependencies,
        'important_stats': list(stats),
        'conditions': conditions,
    }
