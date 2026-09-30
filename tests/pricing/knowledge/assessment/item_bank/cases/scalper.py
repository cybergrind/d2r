"""Upgraded Scalper alternatives preserve ethereal and quantity distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    item = Item(
        'Flying Axe',
        'unique',
        'The Scalper',
        (
            (17, 0, 150),
            (18, 0, 150),
            (119, 0, 25),
            (93, 0, 20),
            (135, 0, 33),
            (60, 0, 4),
            (138, 0, 4),
            (253, 0, 30),
        ),
        ethereal=True,
    )
    for kind in ('named', 'ethereal'):
        roles = tuple(
            f'double-throw-barbarian-guide-the-scalper-{slot}-{kind}-throwing-alternative'
            for slot in ('weapon', 'off-hand')
        )
        variants = [
            ('minimum', item, 'true'),
            (
                'maximum',
                replace(
                    item,
                    raw_stats=tuple(
                        (s, layer, 200 if s in (17, 18) else 6 if s == 60 else v) for s, layer, v in item.raw_stats
                    ),
                ),
                'true',
            ),
            ('nonethereal', replace(item, ethereal=False), 'false' if kind == 'ethereal' else 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), 'unknown' if kind == 'ethereal' else 'true'),
            (
                'invalid-zero-replenishment',
                replace(item, raw_stats=tuple((s, layer, 0 if s == 253 else v) for s, layer, v in item.raw_stats)),
                'unknown',
            ),
            ('native-francisca', replace(item, base='Francisca'), 'false'),
            ('unidentified', replace(item, identified=False), 'false'),
            ('unknown-sockets', replace(item, sockets=None), 'unknown'),
            (
                'unread-replenishment',
                replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 253)),
                'unknown',
            ),
        ]
        for label, candidate, truth in variants:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*(r + '-stats' for r in roles)))
                            for key in ('17:0', '60:0', '119:0', '135:0', '138:0')
                        }
                    )
                )
            yield Case(
                id=f'double-throw/scalper/{kind}/{label}',
                item=candidate,
                context={'player_class': 'Barbarian'},
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else tuple(r + '-stats' for r in roles),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots',
                    'third-parties/d2data/json/uniqueitems.json:/288',
                ),
            )


CASES = tuple(cases())
