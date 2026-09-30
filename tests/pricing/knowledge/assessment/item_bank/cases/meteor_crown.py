"""Meteor's two actual recovery/resistance jewels: useful rolls and preparation."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'meteor-sorceress-4-crown-ages'
JEWEL = SocketItem('Jewel', ((99, 0, 7), *((sid, 0, 11) for sid in (39, 41, 43, 45))), True)
ITEM = Item(
    'Corona',
    'unique',
    'Crown of Ages',
    ((36, 0, 10), (99, 0, 44), (127, 0, 1), *((sid, 0, 42) for sid in (39, 41, 43, 45)), (194, 0, 2)),
    sockets=2,
    socket_contents='filled',
    socket_items=(JEWEL, JEWEL),
)


def cases():
    ctx = {'player_class': 'Sorceress'}
    perfect = replace(JEWEL, raw_stats=((99, 0, 7), *((sid, 0, 15) for sid in (39, 41, 43, 45))))
    rows = [
        ('minimum-jewels', ITEM, ctx, 'true', 'true'),
        (
            'cited-jewels',
            replace(
                ITEM,
                socket_items=(perfect, perfect),
                raw_stats=tuple((sid, layer, 50 if sid in (39, 41, 43, 45) else n) for sid, layer, n in ITEM.raw_stats),
            ),
            ctx,
            'true',
            'true',
        ),
        ('wrong-class', ITEM, {'player_class': 'Paladin'}, 'false', 'true'),
        ('unknown-class', ITEM, {}, 'unknown', 'true'),
        ('ethereal', replace(ITEM, ethereal=True), ctx, 'false', 'true'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), ctx, 'unknown', 'true'),
        (
            'one-socket',
            replace(
                ITEM,
                sockets=1,
                raw_stats=tuple((sid, layer, 1 if sid == 194 else n) for sid, layer, n in ITEM.raw_stats),
                socket_items=(JEWEL,),
            ),
            ctx,
            'false',
            'false',
        ),
        ('empty-sockets', replace(ITEM, socket_contents='empty', socket_items=()), ctx, 'true', 'false'),
        ('unread-second', replace(ITEM, socket_items=(JEWEL,)), ctx, 'true', 'unknown'),
        ('partial-second', replace(ITEM, socket_items=(JEWEL, replace(JEWEL, complete=False))), ctx, 'true', 'unknown'),
        ('wrong-rune', replace(ITEM, socket_items=(JEWEL, SocketItem('Ber Rune'))), ctx, 'true', 'false'),
        (
            'split-modifiers',
            replace(
                ITEM,
                socket_items=(
                    SocketItem('Jewel', ((99, 0, 14),), True),
                    SocketItem('Jewel', tuple((sid, 0, 22) for sid in (39, 41, 43, 45)), True),
                ),
            ),
            ctx,
            'true',
            'false',
        ),
    ]
    for stat in (99, 39, 41, 43, 45):
        below = replace(
            JEWEL, raw_stats=tuple((sid, layer, n - 1 if sid == stat else n) for sid, layer, n in JEWEL.raw_stats)
        )
        rows.append((f'below-{stat}', replace(ITEM, socket_items=(JEWEL, below)), ctx, 'true', 'false'))
    for label, item, context, truth, dependency in rows:
        active = truth == dependency == 'true'
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE, rule_trace=IsPartialDict(truth=truth), dependencies=[IsPartialDict(status=dependency)]
                )
            )
        }
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('36:0', '99:0', '127:0', '39:0', '41:0', '43:0', '45:0')
                    }
                )
            )
        yield Case(
            id='meteor-crown/' + label,
            item=item,
            context=context,
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if 'unknown' in (truth, dependency) else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (ROLE + '-stats',),
            report_contains=(('Crown of Ages', 'Trade tier:') if item.ethereal is not True else ())
            + (('Cited 15% all-resistance jewels',) if label == 'minimum-jewels' else ()),
            report_absent=('Cited 15% all-resistance jewels',) if label == 'cited-jewels' else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/meteor-sorceress/variants/4',
                'third-parties/d2data/json/magicprefix.json:/337',
                'third-parties/d2data/json/magicsuffix.json:/268',
            ),
        )


CASES = tuple(cases())
