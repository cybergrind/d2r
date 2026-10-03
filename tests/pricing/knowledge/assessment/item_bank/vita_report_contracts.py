"""Independent attainable-tier and color expectations for five skill-charm uses.

Native suffix rows 332/333/337/338/339 supply the examples. The level 110
46-50 row is unreachable; ranking uses 5-45, not each suffix's own bracket.
"""

SKILLS = {
    'fissure-druid': (42, 492, 'Elemental Skills (Druid Only)'),
    'lightning-sentry-assassin': (48, 502, 'Traps (Assassin Only)'),
    'lightning-sorceress': (9, 443, 'Lightning Skills (Sorceress Only)'),
    'lightning-strike-amazon': (2, 432, 'Javelin and Spear Skills (Amazon Only)'),
    'poison-nova-necromancer': (17, 455, 'Poison and Bone Skills (Necromancer Only)'),
}
LIFE = {
    5: (5, 10, 8, 332, 'low'),
    13: (11, 15, 7, 333, 'low'),
    14: (11, 15, 7, 333, 'normal'),
    35: (31, 35, 3, 337, 'normal'),
    36: (36, 40, 2, 338, 'normal'),
    40: (36, 40, 2, 338, 'normal'),
    41: (41, 45, 1, 339, 'normal'),
    45: (41, 45, 1, 339, 'perfect'),
}


def vita_checks(build, life, truth, *, role_id=None):
    layer, prefix, skill = SKILLS[build]
    low, high, tier, suffix, quality = LIFE[life]
    skill_text = f'+1 (1-1) to {skill} [T1; T1: 1-1]'
    life_text = f'+{life} (5-45) to Life [T{tier}; T1: 41-45]'
    role = role_id or build + '-main-skiller-vita'
    return {
        'schema_version': 1,
        'role_id': role,
        'configuration_id': role + '-stats',
        'truth': truth,
        'stats': [
            {
                'keys': [f'188:{layer}'],
                'priority': 'desirable',
                'data': {
                    'text': skill_text,
                    'status': 'decoded',
                    'value': 1,
                    'roll_tier': 1,
                    'roll_quality': None,
                    'roll_range': {
                        'min': 1,
                        'max': 1,
                        'quality_range': {'min': 1, 'max': 1},
                        'source': {'record_key': str(prefix)},
                    },
                },
                'body': {'text': skill_text, 'tone': 'default'},
            },
            {
                'keys': ['7:0'],
                'priority': 'supporting',
                'data': {
                    'text': life_text,
                    'status': 'decoded',
                    'value': life,
                    'roll_tier': tier,
                    'roll_tier_count': 8,
                    'roll_quality': quality,
                    'roll_range': {
                        'min': low,
                        'max': high,
                        'quality_range': {'min': 5, 'max': 45},
                        'source': {'record_key': str(suffix)},
                    },
                },
                'body': {'text': life_text, 'tone': quality if quality in {'perfect', 'low'} else 'default'},
            },
        ],
    }
