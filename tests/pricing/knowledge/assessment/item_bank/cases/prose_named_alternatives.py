"""Explicit alternatives remain useful without invented socket prerequisites."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    (
        'lightning-fury-amazon-guide-3-stormshield',
        'Amazon',
        Item(
            'Monarch',
            'unique',
            'Stormshield',
            ((36, 0, 35), (102, 0, 35), (20, 0, 25), (41, 0, 25), (43, 0, 60), (0, 0, 30)),
        ),
        ('36:0', '102:0', '20:0', '41:0', '43:0', '0:0'),
        'pricing/data/wp-a-builds.json:/lightning-fury-amazon-guide/variants/3',
    ),
    (
        'lightning-sentry-assassin-2-griffon-eye',
        'Assassin',
        Item(
            'Diadem', 'unique', "Griffon's Eye", ((127, 0, 1), (105, 0, 25), (330, 0, 10), (334, 0, 15), (31, 0, 150))
        ),
        ('127:0', '105:0', '330:0', '334:0', '31:0'),
        'pricing/data/wp-a-builds.json:/lightning-sentry-assassin/variants/2',
    ),
)


def cases():
    for role, klass, item, keys, source in SPECS:
        context = {'player_class': klass}
        examples = [
            ('unsocketed', item, context, 'true'),
            ('empty-socket', replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))), context, 'true'),
            (
                'ist',
                replace(
                    item,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem('Ist Rune'),),
                    raw_stats=(*item.raw_stats, (194, 0, 1)),
                ),
                context,
                'true',
            ),
            (
                'unknown-contents',
                replace(item, sockets=1, socket_contents='unknown', raw_stats=(*item.raw_stats, (194, 0, 1))),
                context,
                'true',
            ),
            ('wrong-class', item, {'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ]
        for label, candidate, ctx, truth in examples:
            expected = {
                'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth), dependencies=[]))
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'prose-alternative/{role}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                report_contains=(item.name,),
                evidence=(source,),
            )


CASES = tuple(cases())
