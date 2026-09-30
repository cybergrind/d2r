"""Mixed Crown sockets require both the actual Ber and Protector's Stone."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'smite-paladin-2-crown-ages'
STONE = SocketItem('Colossal Jewel', ((201, 17103, 1),), True, "Protector's Stone", 424)
BER = SocketItem('Ber Rune')
ITEM = Item(
    'Corona',
    'unique',
    'Crown of Ages',
    ((36, 0, 18), (99, 0, 30), (127, 0, 1), *((sid, 0, 20) for sid in (39, 41, 43, 45)), (194, 0, 2), (201, 17103, 1)),
    sockets=2,
    socket_contents='filled',
    socket_items=(BER, STONE),
)


def cases():
    ctx = {'player_class': 'Paladin'}
    for label, item, context, truth, active in (
        ('native', ITEM, ctx, 'true', True),
        ('reversed', replace(ITEM, socket_items=(STONE, BER)), ctx, 'true', True),
        ('wrong-rune', replace(ITEM, socket_items=(SocketItem('Ist Rune'), STONE)), ctx, 'true', False),
        (
            'wrong-jewel',
            replace(ITEM, socket_items=(BER, SocketItem('Jewel', STONE.raw_stats, True))),
            ctx,
            'true',
            False,
        ),
        *(
            (
                f'wrong-fade-{value}',
                replace(ITEM, socket_items=(BER, replace(STONE, raw_stats=((201, 17103, value),)))),
                ctx,
                'true',
                False,
            )
            for value in (0, 2)
        ),
        ('partial-jewel', replace(ITEM, socket_items=(BER, replace(STONE, complete=False))), ctx, 'true', False),
        ('unknown-contents', replace(ITEM, socket_contents='unknown', socket_items=()), ctx, 'true', False),
        ('empty', replace(ITEM, socket_contents='empty', socket_items=()), ctx, 'true', False),
        (
            'one-socket',
            replace(
                ITEM,
                sockets=1,
                socket_items=(BER,),
                raw_stats=tuple((sid, layer, 1 if sid == 194 else n) for sid, layer, n in ITEM.raw_stats),
            ),
            ctx,
            'false',
            False,
        ),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false', False),
        ('unknown-class', ITEM, {}, 'unknown', False),
        ('ethereal', replace(ITEM, ethereal=True), ctx, 'false', False),
        ('unknown-ethereal', replace(ITEM, ethereal=None), ctx, 'unknown', False),
    ):
        role = {'id': ROLE, 'rule_trace': IsPartialDict(truth=truth)}
        if active or label == 'wrong-rune':
            role['socket_requirement'] = IsPartialDict(item='Ber Rune', confirmed=active)
        expected = {'roles': Contains(IsPartialDict(**role))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        k: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for k in ('36:0', '99:0', '127:0', '39:0', '41:0', '43:0', '45:0', '201:17103')
                    }
                )
            )
        yield Case(
            id='smite-crown/' + label,
            item=item,
            context=context,
            covers=(ROLE,),
            scenario='positive'
            if active
            else 'unknown'
            if 'unknown' in label or label == 'partial-jewel'
            else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (ROLE + '-stats',),
            report_contains=('Crown of Ages', 'Trade tier:') if label != 'ethereal' else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/smite-paladin/variants/2',
                'third-parties/d2data/json/uniqueitems.json:/424',
            ),
        )


CASES = tuple(cases())
