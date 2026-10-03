"""Authored expectations from native Grand Charm affixes, independent of runtime rules."""

from tests.pricing.knowledge.assessment.item_bank.fixed_charm_report_contracts import SUFFIXES, fixed_stat
from tests.pricing.knowledge.assessment.item_bank.vita_report_contracts import vita_checks


# Captured Sharp, Bronze, Steel and Fine source records, not inferred affix IDs.
AR = {
    6: (6, 12, 12, 218, 'low'),
    31: (21, 48, 8, 252, 'low'),
    32: (21, 48, 8, 252, 'normal'),
    49: (49, 76, 5, 253, 'normal'),
    76: (49, 76, 5, 253, 'normal'),
    132: (118, 132, 1, 226, 'perfect'),
}
DAMAGE = {
    1: (1, 3, 4, 251, 'low'),
    2: (1, 3, 4, 251, 'low'),
    3: (1, 3, 4, 251, 'normal'),
    7: (7, 10, 1, 253, 'normal'),
    10: (7, 10, 1, 253, 'perfect'),
}


def variable_stat(key, value, specification, bounds, text):
    low, high, tier, record, quality = specification
    return {
        'keys': [key],
        'priority': 'desirable',
        'data': {
            'text': text,
            'status': 'decoded',
            'value': value,
            'roll_tier': tier,
            'roll_quality': quality,
            'roll_range': {
                'min': low,
                'max': high,
                'quality_range': {'min': bounds[0], 'max': bounds[1]},
                'source': {'record_key': str(record)},
            },
        },
        'body': {'text': text, 'tone': quality if quality in {'perfect', 'low'} else 'default'},
    }


def sharp_checks(role, suffix, truth, *, ar=None, damage=None, life=36):
    stats = []
    if ar is not None:
        stats.append(
            variable_stat('19:0', ar, AR[ar], (6, 132), f'+{ar} (6-132) to Attack Rating [T{AR[ar][2]}; T1: 118-132]')
        )
    if damage is not None:
        stats.append(
            variable_stat(
                '22:0',
                damage,
                DAMAGE[damage],
                (1, 10),
                f'Maximum damage: {damage} (1-10) [T{DAMAGE[damage][2]}; T1: 7-10]',
            )
        )
    if suffix == 'vita':
        # Reuse independently authored attainable life tiers, without a skill assertion.
        stats.append(vita_checks('fissure-druid', life, truth)['stats'][1])
    elif suffix in SUFFIXES:
        key, value, record, label = SUFFIXES[suffix]
        stats.append(
            fixed_stat(
                key, value, record, f'+{value}% ({value}-{value}%) {label} [T1; T1: {value}-{value}%]', 'supporting'
            )
        )
    return {'schema_version': 1, 'role_id': role, 'configuration_id': role + '-stats', 'truth': truth, 'stats': stats}
