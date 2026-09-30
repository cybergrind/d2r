"""Exact guide alternatives whose utility depends on charges, fillers or set pieces."""

from itertools import combinations

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'Stormlash': (
        'unique',
        'Assassin',
        'Weapon',
        ('dragon-talon-assassin',),
        ('93:0', '136:0', '198:2698', '50:0', '51:0', '145:0'),
    ),
    'Spellsteel': (
        'unique',
        'Amazon',
        'Weapon-Swap',
        ('strafe-amazon',),
        ('charge:54', 'charge:87', '105:0', '9:0', '35:0', '27:0'),
    ),
    'Angelic Halo': (
        'set',
        ('Barbarian', 'Amazon'),
        'Rings',
        ('berserk-barbarian', 'strafe-amazon'),
        ('7:0', '74:0', '224:0'),
    ),
    'Angelic Wings': (
        'set',
        ('Barbarian', 'Amazon'),
        'Amulets',
        ('berserk-barbarian', 'double-throw-barbarian-guide', 'strafe-amazon'),
        ('114:0', '7:0'),
    ),
    "Horazon's Secrets": (
        'set',
        'Warlock',
        'Off-Hand',
        ('fire-warlock-guide',),
        ('99:0', '20:0', '3:0', '7:0', '333:0'),
    ),
    'Marrowwalk': (
        'unique',
        'Sorceress',
        'Boots',
        ('meteor-sorceress',),
        ('charge:88', '96:0', '0:0', '2:0', '27:0', '118:0', '16:0'),
    ),
    'Rune Master': ('unique', 'Barbarian', 'Off-Hand', ('berserk-barbarian',), ('80:0', '153:0', '44:0')),
    "Immortal King's Forge": (
        'set',
        'Barbarian',
        'Gloves',
        ('berserk-barbarian', 'double-throw-barbarian-guide'),
        ('0:0', '2:0', '31:0', '93:0'),
    ),
    "Immortal King's Pillar": (
        'set',
        'Barbarian',
        'Boots',
        ('berserk-barbarian', 'double-throw-barbarian-guide'),
        ('96:0', '19:0', '7:0', '31:0', '80:0', '188:32'),
    ),
}


def setup_condition(name):
    if name == 'Stormlash':
        return {
            'all': [
                {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
                {'op': 'socket_runes_equal', 'value': ['Shael Rune']},
            ]
        }
    if name == 'Spellsteel':
        return {'any': [{'op': 'charge_skill', 'skill_id': skill, 'value': 1} for skill in (54, 87)]}
    if name.startswith('Angelic '):
        return {
            'op': 'context_contains',
            'field': 'player_items',
            'value': 'Angelic Wings' if name == 'Angelic Halo' else 'Angelic Halo',
        }
    if name == "Horazon's Secrets":
        companions = ["Horazon's Countenance", "Horazon's Dominion", "Horazon's Hold", "Horazon's Legacy"]
        return {
            'any': [
                {'all': [{'op': 'context_contains', 'field': 'player_items', 'value': n} for n in pair]}
                for pair in combinations(companions, 2)
            ]
        }
    if name == 'Marrowwalk':
        return {'op': 'charge_skill', 'skill_id': 88, 'value': 1}
    if name == 'Rune Master':
        return {
            'all': [
                {'op': 'fact_eq', 'field': 'sockets', 'value': 5},
                {'op': 'socket_runes_equal', 'value': ['Ist Rune'] * 5},
            ]
        }
    # These are the compatible pieces explicitly listed in both reviewed guides.
    companions = [
        n
        for n in ("Immortal King's Will", "Immortal King's Detail", "Immortal King's Forge", "Immortal King's Pillar")
        if n != name
    ]
    return {
        'any': [
            {'all': [{'op': 'context_contains', 'field': 'player_items', 'value': n} for n in pair]}
            for pair in combinations(companions, 2)
        ]
    }


def priority_condition(name, key):
    if key.startswith('charge:'):
        return {'op': 'charge_skill', 'skill_id': int(key.split(':')[1]), 'value': 1}
    observed = {'op': 'stat_at_least', 'key': key, 'value': 1, 'absent_is_zero': True}
    if key.startswith('198:'):
        observed['unit'] = 'percent_chance'
    conditional = {
        'Angelic Halo': ('224:0',),
        'Angelic Wings': ('7:0',),
        "Horazon's Secrets": ('333:0',),
        'Rune Master': ('80:0',),
        "Immortal King's Forge": ('93:0',),
        "Immortal King's Pillar": ('80:0', '188:32'),
    }
    return {'all': [setup_condition(name), observed]} if key in conditional.get(name, ()) else observed


def expand_qualified_equipment(row):
    name = row['item']
    if name not in MEMBERS:
        raise ValueError('Unknown qualified equipment member')
    quality, klass, slot, builds, stats = MEMBERS[name]
    if (
        row['class'] not in (klass if isinstance(klass, tuple) else (klass,))
        or row['slot'] != slot
        or row['build'] not in builds
        or row['side'] != 'player'
    ):
        raise ValueError('Invalid qualified equipment use')
    base = catalog().named[quality, name]['base_definition']
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name, quality),
    ]
    if name == 'Spellsteel':
        must.append({'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in (0, 1)]})
    elif name in ("Horazon's Secrets", 'Stormlash'):
        must.extend(
            [
                {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
                {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in (0, 1)]},
            ]
        )
    elif name == 'Rune Master':
        # The unique rolls 3-5 sockets; existing sockets cannot be increased.
        must.append({'op': 'fact_eq', 'field': 'sockets', 'value': 5})
    else:
        must.extend(
            {'op': 'fact_eq', 'field': k, 'value': v}
            for k, v in (('ethereal', False), ('sockets', 0), ('socket_contents', 'empty'))
        )
    if name == 'Stormlash':
        role = 'Dragon Talon Static Field and Crushing Blow weapon alternative'
        label = 'One socket filled with a verified Shael rune.'
        conditions = [
            'The guide specifies Shael for attack speed. Weapon Enhanced Damage does not increase kick '
            'damage. Static Field needs an actual on-striking proc and is limited by difficulty and target '
            'lightning resistance. Crushing Blow is target-dependent; added lightning damage can accompany '
            'kicks. No complete kick breakpoint is inferred.'
        ]
    elif name == 'Spellsteel':
        role = 'Strafe Teleport and Decrepify charged swap utility'
        label = 'At least one usable Teleport or Decrepify charge.'
        conditions = [
            'Switch to this axe to cast charges. Decrepify must be applied and can be replaced by other '
            'curses; it is not a passive damage bonus. Charge effects do not transfer weapon damage to the '
            'bow. Ethereal copies cannot be recharged when depleted.'
        ]
    elif name.startswith('Angelic '):
        role = 'Angelic ring and amulet attack-rating combination'
        label = 'Equip the complementary Angelic jewelry piece.'
        conditions = [
            'Two rings are not two distinct set pieces. Attack Rating supports eligible attacks and depends '
            'on character level; it does not guarantee a hit. No three-piece magic-find or All Skills bonus '
            'is assumed. Damage Taken Goes To Mana is recovery, not damage absorption.'
        ]
    elif name == "Horazon's Secrets":
        role = 'Fire Warlock three-piece Horazon resistance reduction alternative'
        label = 'Equip two distinct Horazon companion pieces for fire resistance reduction.'
        conditions = [
            'Eldritch skill levels are not Chaos fire skill levels. Fire resistance reduction requires the '
            'active three-piece set; standalone recovery, block, Vitality and life remain separate. No full- '
            'set bonus or socket filler is assumed.'
        ]
    elif name == 'Marrowwalk':
        role = 'Bone Prison charged utility boots alternative'
        label = 'Bone Prison charges available; recharge when depleted.'
        conditions = [
            'Cast Bone Prison to trap the target; it is not a passive buff or a hard-point synergy. Life Tap '
            'charges do not substitute for Bone Prison. Meet the boots requirements and preserve the rest of '
            'the Uber setup.'
        ]
    elif name == 'Rune Master':
        role = 'Five-Ist Berserk off-hand magic-find alternative'
        label = 'Five sockets filled with five verified Ist runes.'
        conditions = [
            'Use as the inactive attacking hand alongside the Berserk main weapon. Off-hand Enhanced Damage '
            'does not improve the main-hand attack. Ethereal is suitable only while this axe is not used to '
            'attack; five Ist fillers are required, not assumed.'
        ]
    else:
        role = 'Immortal King three-piece equipment alternative'
        label = 'Equip two distinct compatible companion pieces from this guide.'
        conditions = [
            'The guide specifies three pieces, including this item. Set bonuses require the active '
            'combination; no extra life/mana leech or full-set bonus is assumed. Observed IAS, magic find '
            'and Combat Skills are evaluated only with the companion setup. Duplicated pieces and the '
            'incompatible two-handed set maul do not satisfy it.'
        ]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': role,
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [base['type']],
        'qualities': [quality],
        'must': {'all': must},
        'depends_on': [{'label': label, 'when': setup_condition(name)}],
        'important_stats': [
            {'charge:88': '204:5665', 'charge:54': '204:3457', 'charge:87': '204:5571'}.get(key, key) for key in stats
        ],
        'conditions': conditions,
    }
