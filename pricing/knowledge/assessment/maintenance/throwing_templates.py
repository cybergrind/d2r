"""Reviewed named throwing weapons: quantity recovery is not melee repair."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


MEMBERS = {
    'The Scalper': {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'upgraded_only': True,
        'important': ('17:0', '18:0', '119:0', '93:0', '135:0', '60:0', '138:0', '253:0'),
        'desirable': ('17:0', '18:0', '119:0', '93:0', '135:0', '60:0'),
        'conditions': (
            'The guide specifies upgraded Flying Axe form. Open Wounds is separate from physical '
            'weapon damage; life leech depends on physical damage and target drain. Mana after '
            'each kill is not mana leech and requires a credited kill. Quantity replenishment '
            'supports ethereal throwing, not unlimited attack pace or melee durability recovery.',
        ),
    },
    "Gargoyle's Bite": {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'important': ('17:0', '18:0', '60:0', '57:0', '58:0', '253:0'),
        'desirable': ('17:0', '18:0', '60:0'),
        'conditions': (
            'The source prefers ethereal for physical throw damage. Quantity replenishment supports '
            'ethereal throwing, not unlimited attack pace or melee durability recovery. Physical leech '
            'does not use added poison damage. Poison is damage over time, not an instant hit multiplier; '
            'Plague Javelin charges require a separate cast and are not passive Double Throw skill levels.',
        ),
    },
    'Deathbit': {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'upgraded_only': True,
        'important': ('17:0', '18:0', '19:0', '141:0', '60:0', '62:0', '253:0'),
        'desirable': ('17:0', '18:0', '19:0', '141:0', '60:0', '62:0'),
        'conditions': (
            'The guide explicitly specifies upgraded Deathbit in Flying Knife form. '
            'Deadly Strike does not add directly to critical chance. Physical leech depends on target drain. '
            'Replenishment permits ethereal quantity recovery, not unlimited continuous throws or '
            'immunity to melee durability loss.',
        ),
    },
    'Lacerator': {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'important': ('17:0', '18:0', '93:0', '135:0', '198:4227', '253:0'),
        'desirable': ('17:0', '18:0', '93:0', '198:4227'),
        'conditions': (
            'Amplify Damage needs an on-striking proc and can be overwritten by '
            'other curses or the weapon flee effect. Open Wounds is separate '
            'from physical damage. Replenishment does not guarantee enough '
            'quantity for continuous throwing; check Throwing Mastery and pace.',
        ),
    },
    'Warshrike': {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'important': ('17:0', '18:0', '93:0', '156:0', '141:0', '253:0'),
        'desirable': ('17:0', '18:0', '93:0', '156:0', '141:0'),
        'conditions': (
            'Pierce combines with Throwing Mastery up to its cap. Deadly Strike '
            'and Critical Strike are separate chances, not simply added percentages. '
            'The Nova proc is incidental spell damage; it does not multiply throws.',
        ),
    },
    "Demon's Arch": {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'important': ('17:0', '18:0', '93:0', '60:0', '253:0'),
        'desirable': ('17:0', '18:0', '93:0', '60:0'),
        'conditions': (
            'Life leech uses physical attack damage and target drain, not the '
            'added fire/lightning damage. Compare the full throwing speed setup '
            'and quantity sustain; the other hand is a separate item.',
        ),
    },
    'Gimmershred': {
        'class': 'Barbarian',
        'sustain': 'throwing_mastery',
        'important': ('17:0', '18:0', '93:0', '254:0'),
        'desirable': ('17:0', '18:0', '93:0'),
        'conditions': (
            'This Double Throw alternative has no native quantity replenishment. '
            'Sustained ethereal use relies on Throwing Mastery quantity saving '
            'and replenishment on critical hits; the hover does not prove that '
            'skill setup or remaining quantity. Cold damage can destroy corpses '
            'needed for Find Item. Ethereal increases physical, not elemental damage.',
        ),
    },
    'Wraith Flight': {
        'class': 'Barbarian',
        'sustain': 'replenishes',
        'always_ethereal': True,
        'important': ('17:0', '18:0', '60:0', '138:0', '253:0'),
        'desirable': ('17:0', '18:0', '60:0'),
        'conditions': (
            'This unique is inherently ethereal and replenishes quantity. It has '
            'no IAS; compare its slow base against the complete throwing setup. '
            'Life leech needs physical damage and target drain; mana after each '
            'kill is separate from mana leech.',
        ),
    },
    "Titan's Revenge": {
        'class': 'Amazon',
        'sustain': 'replenishes',
        'important': ('83:0', '188:2', '96:0', '0:0', '2:0', '17:0', '18:0', '60:0', '253:0'),
        'desirable': ('83:0', '188:2', '96:0'),
        'conditions': (
            'Amazon and Javelin skills support lightning skills. Enhanced Damage '
            'and ethereal improve the physical hit, not the lightning spell damage. '
            'Life leech needs physical damage and target drain. Replenishment '
            'supports ethereal quantity recovery, but throwing may outpace it; '
            'upgrading also increases equip requirements.',
        ),
    },
    'Thunderstroke': {
        'class': 'Amazon',
        'sustain': 'repair',
        'important': ('188:2', '334:0', '93:0', '17:0', '18:0'),
        'desirable': ('188:2', '334:0', '93:0'),
        'conditions': (
            'Prioritize Javelin skills and enemy lightning resistance reduction. '
            'Resistance reduction alone does not break immunity. Added Lightning '
            'Bolt levels do not grant hard-point synergies to Lightning Fury or '
            'Lightning Strike. This weapon has no native quantity replenishment; '
            'ethereal copies cannot be repaired or refilled for sustained Amazon use.',
        ),
    },
}


def expand_named_throwing(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['class'] not in CLASS_NAMES
        or row['class'] != MEMBERS[name]['class']
        or row['side'] != 'player'
        or row['slot'] not in ('Weapon', 'Off-Hand')
    ):
        raise ValueError('Invalid named throwing weapon membership')
    member = MEMBERS[name]
    ethereal_only = row.get('ethereal_only', False)
    if type(ethereal_only) is not bool:
        raise ValueError('Named throwing ethereal selector must be boolean')
    if ethereal_only and (row['build'] != 'double-throw-barbarian-guide' or member['class'] != 'Barbarian'):
        raise ValueError('Exact ethereal alternative requires the reviewed Double Throw build')
    if member['sustain'] == 'throwing_mastery' and row['build'] != 'double-throw-barbarian-guide':
        raise ValueError('Throwing Mastery sustain requires the reviewed Double Throw build')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        named_base_condition(name, 'unique'),
        *[
            {'op': 'fact_eq', 'field': k, 'value': v}
            for k, v in (
                ('identified', True),
                ('sockets', 0),
                ('socket_contents', 'empty'),
            )
        ],
    ]
    if member.get('upgraded_only'):
        must.append(
            {
                'op': 'fact_eq',
                'field': 'base_code',
                'value': catalog().named['unique', name]['base_definition']['ultracode'],
            }
        )
    if member['sustain'] == 'repair':
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
    elif member['sustain'] == 'replenishes':
        must.append(
            {'op': 'stat_at_least', 'key': '253:0', 'value': 1, 'absent_is_zero': True, 'unit': 'replenishment_rate'}
        )
    if member.get('always_ethereal') or ethereal_only:
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
    definition = catalog().named['unique', name]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class', 'ethereal_only')},
        'role': 'Throwing weapon alternative with quantity-sustain conditions',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {'all': must},
        'important_stats': list(member['important']),
        'conditions': [*member['conditions'], *row.get('conditions', [])],
    }
