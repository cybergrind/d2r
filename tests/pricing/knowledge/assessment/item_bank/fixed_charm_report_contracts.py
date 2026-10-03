"""Native fixed skill/suffix expectations, authored independently of appraisal rules."""

from tests.pricing.knowledge.assessment.item_bank.vita_report_contracts import SKILLS


SUFFIXES = {
    'balance': ('99:0', 12, 265, 'Faster Hit Recovery'),
    'inertia': ('96:0', 7, 399, 'Faster Run/Walk'),
}


def fixed_stat(key, value, record, text, priority):
    return {
        'keys': [key],
        'priority': priority,
        'data': {
            'text': text,
            'status': 'decoded',
            'value': value,
            'roll_tier': 1,
            'roll_quality': None,
            'roll_range': {
                'min': value,
                'max': value,
                'quality_range': {'min': value, 'max': value},
                'source': {'record_key': str(record)},
            },
        },
        'body': {'text': text, 'tone': 'default'},
    }


def fixed_charm_checks(build, suffix, truth, *, role_id=None):
    layer, prefix, skill = SKILLS[build]
    role = role_id or f'{build}-main-skiller-{suffix}'
    stats = [fixed_stat(f'188:{layer}', 1, prefix, f'+1 (1-1) to {skill} [T1; T1: 1-1]', 'desirable')]
    if suffix != 'plain':
        key, value, record, label = SUFFIXES[suffix]
        stats.append(
            fixed_stat(
                key,
                value,
                record,
                f'+{value}% ({value}-{value}%) {label} [T1; T1: {value}-{value}%]',
                'supporting',
            )
        )
    return {
        'schema_version': 1,
        'role_id': role,
        'configuration_id': role + '-stats',
        'truth': truth,
        'stats': stats,
    }
