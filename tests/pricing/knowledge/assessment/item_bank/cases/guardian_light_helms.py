"""Guardian's Light Shako configurations require the actual named linked jewel."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('blessed-hammer-paladin-2-harlequin', 'Paladin', True),
    ('berserk-barbarian-1-harlequin', 'Barbarian', False),
    ('abyss-warlock-build-guide-2-harlequin', 'Warlock', True),
    ('echoing-strike-warlock-guide-2-harlequin', 'Warlock', True),
)
CHILD = SocketItem('Colossal Jewel', ((357, 0, 5), (358, 0, 5)), True, "Guardian's Light", 425)
NATIVE = ((127, 0, 2), (80, 0, 65), (36, 0, 10), (194, 0, 1), (357, 0, 5), (358, 0, 5))
ITEM = Item('Shako', 'unique', 'Harlequin Crest', NATIVE, sockets=1, socket_contents='filled', socket_items=(CHILD,))


def cases():
    for intrinsic, klass, fcr in SPECS:
        role = intrinsic + '-guardian-light'
        context = {'player_class': klass, **({'player_total_fcr': 125} if fcr else {})}
        examples = [
            ('minimum', ITEM, context, 'true'),
            (
                'wrong-jewel',
                replace(ITEM, socket_items=(replace(CHILD, name=None, unique_table_id=None),)),
                context,
                'false',
            ),
            (
                'partial-jewel',
                replace(ITEM, socket_items=(replace(CHILD, complete=False, raw_stats=()),)),
                context,
                'unknown',
            ),
            ('unread-jewel', replace(ITEM, socket_items=()), context, 'unknown'),
            ('empty', replace(ITEM, socket_contents='empty', socket_items=()), context, 'false'),
            ('wrong-class', ITEM, {**context, 'player_class': 'Druid'}, 'false'),
            ('unknown-class', ITEM, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ]
        if fcr:
            examples += [
                ('below-fcr', ITEM, {**context, 'player_total_fcr': 124}, 'false'),
                ('unknown-fcr', ITEM, {'player_class': klass}, 'unknown'),
            ]
        for label, candidate, ctx, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('127:0', '80:0', '358:0')
                        }
                    )
                )
            yield Case(
                id=f'guardian-light-helm/{intrinsic}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations={'357:0': (role + '-stats',)}
                if klass == 'Barbarian' or intrinsic.startswith('echoing-')
                else {},
                report_contains=('Harlequin Crest',),
                evidence=('third-parties/d2data/json/uniqueitems.json:/425',),
            )


CASES = tuple(cases())
