"""Current Expansion suffix rolls and four empty sockets for Strafe armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for suffix, stat, minimum, maximum, affix, position in (
        ('stability', 99, 24, 24, 264, 1),
        ('precision', 2, 10, 15, 254, 2),
    ):
        role = f'strafe-amazon-{suffix}-shroud-socket-base'
        config = role + '-stats'
        raw = ((194, 0, 4), (stat, 0, minimum))
        original = Item(
            'Dusk Shroud', 'magic', raw_stats=raw, sockets=4, affix_records=(('prefix', 422), ('suffix', affix))
        )
        ctx = {'player_class': 'Amazon'}
        for label, item, context, truth in (
            ('native', original, ctx, 'true'),
            ('maximum', replace(original, raw_stats=((194, 0, 4), (stat, 0, maximum))), ctx, 'true'),
            (
                'legacy-or-lower',
                replace(original, raw_stats=((194, 0, 4), (stat, 0, 20 if stat == 99 else 9)), affix_records=None),
                ctx,
                'false',
            ),
            ('unread-suffix', replace(original, raw_stats=((194, 0, 4),), affix_records=None), ctx, 'unknown'),
            (
                'known-no-suffix',
                replace(original, raw_stats=((194, 0, 4),), affix_records=None, complete=True),
                ctx,
                'false',
            ),
            (
                'three-sockets',
                replace(original, sockets=3, raw_stats=((194, 0, 3), (stat, 0, minimum)), affix_records=None),
                ctx,
                'false',
            ),
            (
                'unknown-sockets',
                replace(original, sockets=None, raw_stats=((stat, 0, minimum),), affix_records=None),
                ctx,
                'unknown',
            ),
            ('unknown-contents', replace(original, socket_contents='unknown'), ctx, 'unknown'),
            (
                'one-filled',
                replace(
                    original,
                    socket_contents='filled',
                    socket_items=(SocketItem('Jewel', ((93, 0, 15),)),),
                    raw_stats=(*raw, (93, 0, 15)),
                ),
                ctx,
                'false',
            ),
            ('ethereal', replace(original, ethereal=True), ctx, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({f'{stat}:0': IsPartialDict(configuration_ids=Contains(config))})
                )
            yield Case(
                id=f'strafe-magic-armor/{suffix}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(('31:0', '17:0', '18:0', '93:0'), (config,)),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/strafe-amazon/slots/Body Armor/{position}',
                    'third-parties/d2data/json/magicprefix.json:/422',
                    f'third-parties/d2data/json/magicsuffix.json:/{affix}',
                ),
            )


CASES = tuple(cases())
