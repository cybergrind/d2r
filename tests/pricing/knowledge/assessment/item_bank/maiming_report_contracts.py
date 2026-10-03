"""Independent ranges for captured prefix/suffix damage on Grand Charms."""

from tests.pricing.knowledge.assessment.item_bank.sharp_report_contracts import sharp_checks


# Source records: Fine251, Sharp253; Craftsmanship676, Quality677, Maiming678.
DAMAGE = {
    2: (2, 4, 14, 251, 676, 'low'),
    4: (3, 5, 12, 251, 677, 'low'),
    5: (3, 5, 12, 251, 677, 'normal'),
    10: (10, 14, 1, 253, 678, 'normal'),
    14: (10, 14, 1, 253, 678, 'perfect'),
}


def maiming_checks(role, truth, *, ar=None, damage=None):
    checks = sharp_checks(role, None, truth, ar=ar)
    if damage is not None:
        low, high, tier, prefix, suffix, quality = DAMAGE[damage]
        text = f'Maximum damage: {damage} (2-14) [T{tier}; T1: 10-14]'
        checks['stats'].append(
            {
                'keys': ['22:0'],
                'priority': 'desirable',
                'data': {
                    'text': text,
                    'status': 'decoded',
                    'value': damage,
                    'roll_tier': tier,
                    'roll_quality': quality,
                    'roll_range': {
                        'min': low,
                        'max': high,
                        'quality_range': {'min': 2, 'max': 14},
                        'source': [{'record_key': str(prefix)}, {'record_key': str(suffix)}],
                    },
                },
                'body': {'text': text, 'tone': quality if quality in {'low', 'perfect'} else 'default'},
            }
        )
    return checks
