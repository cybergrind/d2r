"""Holy Bolt's casting weapon accepts native minimum compound-jewel rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fist-of-the-heavens-paladin-4-hand-support-jewel'
CHILD = SocketItem('Jewel', ((99, 0, 7), (39, 0, 21), (41, 0, 5), (43, 0, 5), (45, 0, 5), (114, 0, 7)), True)
NATIVE = ((83, 3, 2), (107, 101, 4), (107, 121, 2), (27, 0, 15), (17, 0, 130), (18, 0, 130), (194, 0, 1))
ITEM = Item(
    'Divine Scepter',
    'unique',
    'Hand of Blessed Light',
    (*NATIVE, *CHILD.raw_stats),
    ethereal=True,
    sockets=1,
    socket_contents='filled',
    socket_items=(CHILD,),
)


def cases():
    ctx = {'player_class': 'Paladin'}
    perfect = replace(CHILD, raw_stats=((99, 0, 7), (39, 0, 40), (41, 0, 10), (43, 0, 10), (45, 0, 10), (114, 0, 12)))
    examples = [
        ('native-minimum', ITEM, ctx, 'true'),
        ('perfect-jewel', replace(ITEM, raw_stats=(*NATIVE, *perfect.raw_stats), socket_items=(perfect,)), ctx, 'true'),
        ('nonethereal', replace(ITEM, ethereal=False), ctx, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), ctx, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unread-child', replace(ITEM, socket_items=()), ctx, 'unknown'),
        ('partial-child', replace(ITEM, socket_items=(replace(CHILD, complete=False),)), ctx, 'unknown'),
        ('wrong-rune', replace(ITEM, socket_items=(SocketItem('Ber Rune'),)), ctx, 'false'),
        ('empty', replace(ITEM, socket_contents='empty', socket_items=()), ctx, 'false'),
    ]
    for stat, _, minimum in CHILD.raw_stats:
        below = replace(
            CHILD, raw_stats=tuple((sid, layer, minimum - 1 if sid == stat else n) for sid, layer, n in CHILD.raw_stats)
        )
        examples.append((f'below-{stat}', replace(ITEM, socket_items=(below,)), ctx, 'false'))
    for label, item, context, truth in examples:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('83:3', '107:101', '107:121', '99:0', '39:0', '114:0')
                    }
                )
            )
        yield Case(
            id='holy-bolt-hand/' + label,
            item=item,
            context=context,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=('Hand of Blessed Light', 'Trade tier:'),
            evidence=('pricing/raw/mr/planners/s10106pr.json:/data', 'third-parties/d2data/json/uniqueitems.json:/146'),
        )


CASES = tuple(cases())
