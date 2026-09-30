"""Ravenlore native utility and the separately verified Ubers Fire Facet."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


NATIVE = ((188, 42, 3), (333, 0, 10), (1, 0, 20), (16, 0, 120), *((sid, 0, 15) for sid in (39, 41, 43, 45)))
ITEM = Item('Sky Spirit', 'unique', 'Ravenlore', NATIVE, ethereal=False, sockets=0, socket_contents='empty')


def socketed(roll=3, table=394):
    jewel = SocketItem(
        'Jewel', ((329, 0, roll), (333, 0, roll)), complete=True, name='Rainbow Facet', unique_table_id=table
    )
    return replace(
        ITEM,
        sockets=1,
        socket_contents='filled',
        socket_items=(jewel,),
        raw_stats=(
            *tuple((sid, layer, value + roll if sid == 333 else value) for sid, layer, value in NATIVE),
            (329, 0, roll),
            (194, 0, 1),
        ),
    )


def cases():
    context = {'player_class': 'Druid'}
    low = socketed()
    examples = [
        ('unsocketed', ITEM, context, 'true', 'false'),
        ('minimum-die-facet', low, context, 'true', 'true'),
        ('perfect-up-facet', socketed(5, 398), context, 'true', 'true'),
        ('empty-socket', replace(ITEM, sockets=1), context, 'true', 'false'),
        ('unread-child', replace(low, socket_items=()), context, 'true', 'unknown'),
        (
            'partial-child',
            replace(low, socket_items=(replace(low.socket_items[0], complete=False),)),
            context,
            'true',
            'unknown',
        ),
        (
            'ordinary-jewel',
            replace(low, socket_items=(SocketItem('Jewel', ((329, 0, 3), (333, 0, 3)), True),)),
            context,
            'true',
            'false',
        ),
        (
            'cold-facet',
            replace(low, socket_items=(SocketItem('Jewel', ((331, 0, 3), (335, 0, 3)), True, 'Rainbow Facet', 393),)),
            context,
            'true',
            'false',
        ),
        ('ethereal', replace(low, ethereal=True), context, 'false', 'true'),
        ('unread-ethereal', replace(low, ethereal=None), context, 'unknown', 'true'),
        ('wrong-class', low, {'player_class': 'Sorceress'}, 'false', 'true'),
        ('unknown-class', low, {}, 'unknown', 'true'),
    ]
    for stat in (329, 333):
        for value in (2, 6):
            child = replace(
                low.socket_items[0],
                raw_stats=((329, 0, value if stat == 329 else 3), (333, 0, value if stat == 333 else 3)),
            )
            examples.append(
                (f'out-of-range-{stat}-{value}', replace(low, socket_items=(child,)), context, 'true', 'false')
            )
    for variant in ('standard', 'ubers'):
        role = f'fissure-player-{variant}-ravenlore'
        config = role + '-stats'
        for label, item, ctx, truth, payload in examples:
            usable = truth == 'true' and (variant == 'standard' or payload == 'true')
            role_expect = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
            if variant == 'ubers':
                role_expect['dependencies'] = Contains(IsPartialDict(status=payload))
            expected = {'roles': Contains(IsPartialDict(**role_expect))}
            if usable:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('188:42', '333:0', '39:0')}
                    )
                )
            yield Case(
                id=f'ravenlore/{variant}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if usable else 'unknown' if 'unknown' in (truth, payload) else 'negative',
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if usable else (config,),
                report_contains=('Ravenlore', 'Trade tier:'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/fissure-druid/variants/{1 if variant == "standard" else 3}',
                    'third-parties/d2data/json/uniqueitems.json:/350',
                    'third-parties/d2data/json/uniqueitems.json:/394',
                ),
            )


CASES = tuple(cases())
