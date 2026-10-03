"""Authored native Lightning skill and complete compact-report expectations."""


def lightning_plain(truth):
    text = '+1 (1-1) to Lightning Skills (Sorceress Only) [T1; T1: 1-1]'
    prefix = '  ● [desirable] '
    contract = {
        'schema_version': 1,
        'role_id': 'lightning-sorceress-main-skiller-plain',
        'configuration_id': 'lightning-sorceress-main-skiller-plain-stats',
        'truth': truth,
        'stats': [
            {
                'keys': ['188:9'],
                'data': {
                    'status': 'decoded',
                    'text': text,
                    'value': 1,
                    'roll_tier': 1,
                    'roll_quality': None,
                    'roll_range': {
                        'min': 1,
                        'max': 1,
                        'quality_range': {'min': 1, 'max': 1},
                        'source': {'record_key': '443'},
                    },
                },
                'line': {
                    'text': prefix + text,
                    'tone': 'default',
                    'spans': [
                        {'text': prefix, 'tone': 'stat_desirable'},
                        {'text': text, 'tone': 'default'},
                    ],
                },
            }
        ],
        'price': {'estimate_ist': None, 'unavailable_reason': 'no_matches'},
    }

    lines = [
        {'text': 'Item: Magic Grand Charm', 'tone': 'magic'},
        {'text': 'Ethereal: no', 'tone': 'default'},
        {'text': 'Observed stats:', 'tone': 'heading'},
        contract['stats'][0]['line'],
        {'text': 'Build use', 'tone': 'heading'},
        {
            'text': '  This item: 1 confirmed / 0 conditional builds'
            if truth == 'true'
            else '  This item: 0 confirmed / 1 conditional builds',
            'tone': 'default',
        },
    ]
    if truth != 'false':
        state = 'confirmed' if truth == 'true' else 'conditional'
        lines.append(
            {
                'text': '  player · Lightning skiller · Main alternatives · ' + state + ': Lightning Sorceress',
                'tone': 'default',
            }
        )
    if truth != 'true':
        lines.append(
            {
                'text': '  player · starter skill-tree charm · Starter · conditional: Lightning Sorceress',
                'tone': 'default',
            }
        )
    lines.append({'text': "Price: unknown — no offline listings match this item's variant.", 'tone': 'default'})
    contract['osd'] = lines
    return contract
