"""Barbarian IK helm alternatives keep native rolls separate from socket fillers."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


RAW = ((188, 34, 2), (79, 0, 37), (80, 0, 25), (89, 0, 4), (194, 0, 2))
ITEM = Item('Avenger Guard', 'set', "Immortal King's Will", RAW, sockets=2, named_table_id=70)


def cases(role, prefix, locator):
    config = role + '-stats'
    context = {'player_class': 'Barbarian'}
    for label, item, ctx, truth in (
        ('minimum-magic-find', ITEM, context, 'true'),
        ('maximum-magic-find', replace(ITEM, raw_stats=(*RAW[:2], (80, 0, 40), *RAW[3:])), context, 'true'),
        ('exceptional', replace(ITEM, base='Slayer Guard'), context, 'true'),
        ('elite', replace(ITEM, base='Guardian Crown'), context, 'true'),
        (
            'topaz-filled',
            replace(
                ITEM,
                raw_stats=(*RAW[:2], (80, 0, 73), *RAW[3:]),
                socket_contents='filled',
                socket_items=(SocketItem('Perfect Topaz'),) * 2,
            ),
            context,
            'true',
        ),
        ('one-socket', replace(ITEM, sockets=1, raw_stats=(*RAW[:4], (194, 0, 1))), context, 'false'),
        (
            'unknown-sockets',
            replace(ITEM, sockets=None, socket_contents='unknown', raw_stats=RAW[:4]),
            context,
            'unknown',
        ),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Amazon'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('188:34', '79:0', '80:0')}
                )
            )
        yield Case(
            id=prefix + label,
            item=item,
            context=ctx,
            covers=(role,),
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (config,),
            report_contains=(
                "Immortal King's Will",
                'Trade tier:',
                'Sockets: 2',
                *(('Perfect Topaz',) if label == 'topaz-filled' else ('(25-40%)',)),
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:' + locator,
                "third-parties/d2data/json/setitems.json:/Immortal King's Will",
            ),
        )


CASES = tuple(
    case
    for role, prefix, locator in (
        (
            'gold-find-barbarian-immortal-king-s-will-equipment-tail-alternative',
            'gold-find-ik-will/',
            '/gold-find-barbarian/slots/Helmets/2',
        ),
        (
            'double-throw-barbarian-guide-immortal-king-s-will-equipment-tail-alternative',
            'double-throw-ik-will/',
            '/double-throw-barbarian-guide/slots/Helmets/15',
        ),
    )
    for case in cases(role, prefix, locator)
)
