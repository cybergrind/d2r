"""Holy Bolt's Ber Shako and Um Herald are separate equipped-set components."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    (
        'harlequin-ber',
        'Shako',
        'Harlequin Crest',
        'Ber Rune',
        ((127, 0, 2), (80, 0, 50), (36, 0, 18)),
        ('127:0', '36:0'),
    ),
    (
        'herald-um-swap',
        'Gilded Shield',
        'Herald of Zakarum',
        'Um Rune',
        (
            (83, 3, 2),
            (188, 24, 2),
            (16, 0, 150),
            (102, 0, 30),
            (20, 0, 30),
            *((sid, 0, 72) for sid in (39, 41, 43, 45)),
        ),
        ('83:3', '188:24', '39:0'),
    ),
)


def cases():
    for suffix, base, name, rune, stats, keys in SPECS:
        role = 'fist-of-the-heavens-paladin-4-' + suffix
        item = Item(
            base,
            'unique',
            name,
            (*stats, (194, 0, 1)),
            ethereal=False,
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem(rune),),
        )
        context = {'player_class': 'Paladin'}
        for label, candidate, ctx, truth in (
            ('native-minimum', item, context, 'true'),
            ('wrong-rune', replace(item, socket_items=(SocketItem('Ist Rune'),)), context, 'false'),
            ('unknown-child', replace(item, socket_items=()), context, 'unknown'),
            ('empty-socket', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('no-full-fcr', item, {**context, 'player_total_fcr': 0}, 'true'),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        slot='Helmet' if suffix == 'harlequin-ber' else 'Off-Hand-Swap',
                        rule_trace=IsPartialDict(truth=truth),
                    )
                )
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'holy-bolt-helm-shield/{suffix}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                report_contains=(name, 'Trade tier:'),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/4',
                    'pricing/raw/mr/planners/s10106pr.json:/data',
                ),
            )


CASES = tuple(cases())
