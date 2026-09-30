"""Starter Insight: legal Act 2 polearms and bearer-specific stat benefits."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_starter_merc import case
from tests.pricing.knowledge.assessment.item_bank.models import Item


def cases():
    result = []
    role = 'zeal-paladin-insight-act-2-might'
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Bill',
            quality,
            'Insight',
            (
                (151, 120, 12),
                (17, 0, 200),
                (18, 0, 200),
                (97, 9, 1),
                (119, 0, 180),
                (105, 0, 35),
                (0, 0, 5),
                (1, 0, 5),
                (2, 0, 5),
                (3, 0, 5),
                (21, 0, 9),
            ),
            runeword='Insight',
            sockets=4,
            socket_contents='filled',
        )
        keys = ('151:120', '17:0', '97:9', '119:0', '0:0', '2:0', '21:0')
        result.extend(
            (
                case(role, quality + '/low-rolls', item, 'Act 2 Might', keys, absent=('105:0', '1:0', '3:0')),
                case(
                    role,
                    quality + '/ethereal-elite',
                    replace(item, base='Thresher', ethereal=True),
                    'Act 2 Might',
                    keys,
                ),
                case(
                    role, quality + '/illegal-capacity', replace(item, base='Bardiche'), 'Act 2 Might', keys, 'negative'
                ),
                case(role, quality + '/wrong-merc', item, 'Act 5 Frenzy', keys, 'negative'),
                case(role, quality + '/unknown-merc', item, None, keys, 'unknown'),
            )
        )
    return tuple(result)


CASES = cases()
