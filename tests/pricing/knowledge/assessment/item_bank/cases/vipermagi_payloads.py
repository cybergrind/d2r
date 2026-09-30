"""Enchant Fire Facet and Nova Ist setups require actual armor socket contents."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ITEM = Item(
    'Serpentskin Armor',
    'unique',
    'Skin of the Vipermagi',
    ((105, 0, 30), (127, 0, 1), (16, 0, 120), (35, 0, 9), *((sid, 0, 20) for sid in (39, 41, 43, 45)), (194, 0, 1)),
    ethereal=False,
    sockets=1,
    socket_contents='filled',
)
FACET = SocketItem('Jewel', ((329, 0, 3), (333, 0, 3)), True, 'Rainbow Facet', 394)


def cases():
    for build, suffix, child, extra in (
        ('enchant-sorceress', 'fire-facet', FACET, ((329, 0, 3), (333, 0, 3))),
        ('nova-sorceress-guide', 'ist', SocketItem('Ist Rune'), ((80, 0, 25),)),
    ):
        role = f'{build}-2-vipermagi-{suffix}'
        item = replace(ITEM, raw_stats=(*ITEM.raw_stats, *extra), socket_items=(child,))
        context = {'player_class': 'Sorceress', 'player_total_fcr': 105}
        rows = [
            ('native-minimum', item, context, 'true'),
            ('unknown-child', replace(item, socket_items=()), context, 'unknown'),
            ('wrong-rune', replace(item, socket_items=(SocketItem('Ral Rune'),)), context, 'false'),
            ('empty-socket', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {'player_total_fcr': 105}, 'unknown'),
            ('upgraded', replace(item, base='Wyrmhide'), context, 'true' if suffix == 'fire-facet' else 'false'),
            ('below-fcr', item, {**context, 'player_total_fcr': 104}, 'true' if suffix == 'fire-facet' else 'false'),
            ('unknown-fcr', item, {'player_class': 'Sorceress'}, 'true' if suffix == 'fire-facet' else 'unknown'),
        ]
        if suffix == 'fire-facet':
            rows.extend(
                (
                    (
                        'perfect-facet',
                        replace(
                            item,
                            socket_items=(replace(FACET, raw_stats=((329, 0, 5), (333, 0, 5))),),
                            raw_stats=(*ITEM.raw_stats, (329, 0, 5), (333, 0, 5)),
                        ),
                        context,
                        'true',
                    ),
                    (
                        'partial-facet',
                        replace(item, socket_items=(replace(FACET, complete=False),)),
                        context,
                        'unknown',
                    ),
                    (
                        'wrong-element',
                        replace(
                            item,
                            socket_items=(SocketItem('Jewel', ((330, 0, 3), (334, 0, 3)), True, 'Rainbow Facet', 392),),
                        ),
                        context,
                        'false',
                    ),
                )
            )
            for stat in (329, 333):
                for value in (2, 6):
                    invalid = replace(
                        FACET, raw_stats=((329, 0, value if stat == 329 else 3), (333, 0, value if stat == 333 else 3))
                    )
                    rows.append(
                        (f'out-of-range-{stat}-{value}', replace(item, socket_items=(invalid,)), context, 'false')
                    )
        config = role + '-stats'
        for label, candidate, ctx, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in (
                                '105:0',
                                '127:0',
                                *(('329:0', '333:0') if suffix == 'fire-facet' else ('80:0',)),
                            )
                        }
                    )
                )
            yield Case(
                id=f'vipermagi-payload/{suffix}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=('Skin of the Vipermagi', 'Trade tier:'),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/variants/2',),
            )


CASES = tuple(cases())
