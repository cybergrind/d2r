"""Reviewed generic charged-item labels; decorated skill combinations stay separate."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.adapters.capture import bases_by_code


# Skill, native family, explicit base (if present), native charged suffix record.
MEMBERS = {
    'Staff of Teleportation': (54, 'staf', None, '532'),
    'Teleport Charge Staff': (54, 'staf', None, '532'),
    'Long Staff of Teleportation': (54, 'staf', 'Long Staff', '532'),
    'Battle Staff of Teleportation': (54, 'staf', 'Battle Staff', '532'),
    'Amulet of Teleportation': (54, 'amul', 'Amulet', '533'),
    'Teleport Charge Amulet': (54, 'amul', 'Amulet', '533'),
    'Wand of Lower Resistance': (91, 'wand', None, '594'),
    'Lower Resist Charge Wand': (91, 'wand', None, '594'),
    'Wand of Life Tap': (82, 'wand', None, '578'),
    'Bone Wand of Life Tap': (82, 'wand', 'Bone Wand', '578'),
}
SKILLS = {54: 'Teleport', 91: 'Lower Resist', 82: 'Life Tap'}


def expand_charge_utility(row):
    label = row['item']
    if label not in MEMBERS or row['class'] not in CLASS_NAMES or row['side'] != 'player':
        raise ValueError('Invalid charged utility template membership')
    skill, family, base, _ = MEMBERS[label]
    if row['slot'] != ('Amulets' if family == 'amul' else 'Weapon-Swap'):
        raise ValueError('Charged utility has the wrong equipment slot')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        {'op': 'charge_skill', 'skill_id': skill, 'value': 0},
    ]
    if base:
        code = next(code for code, entry in bases_by_code().items() if entry['name'] == base)
        must.append({'op': 'fact_eq', 'field': 'base_code', 'value': code})
    if family == 'amul':
        must.extend(
            {'op': 'fact_eq', 'field': key, 'value': value}
            for key, value in (('ethereal', False), ('sockets', 0), ('socket_contents', 'empty'))
        )
    conditions = [
        'Equip this utility item and meet its requirements before using charges; '
        'other slots and breakpoints are separate.',
    ]
    if family != 'amul':
        conditions.append('Ethereal copies can use remaining charges but cannot be recharged when depleted.')
    if skill == 91:
        conditions.append(
            'Lower Resist effectiveness depends on the target; charges do not guarantee an immunity break.'
        )
    if skill == 82:
        conditions.append(
            'Apply Life Tap to the target; eligible physical attacks and the rest of the setup remain necessary.'
        )
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': f'{SKILLS[skill]} charged-item utility alternative',
        'review_status': 'reviewed_candidate_rule',
        'types': [family],
        'qualities': ['magic', 'rare'],
        'must': {'all': must},
        'depends_on': [
            {
                'label': f'{SKILLS[skill]} charges available; recharge non-ethereal copies when empty.',
                'when': {'op': 'charge_skill', 'skill_id': skill, 'value': 1},
            }
        ],
        'conditions': conditions,
    }
