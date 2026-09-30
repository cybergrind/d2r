"""Kuko's Enchant delivery and Shael preparation are separate from physical ED."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'enchant-sorceress-kuko-shakaku-budget-delivery-weapon'
CONFIG = ROLE + '-stats'
RAW = ((156, 0, 50), (158, 0, 7), (17, 0, 150), (18, 0, 150), (48, 0, 40), (49, 0, 180), (188, 0, 3), (107, 27, 3))


def cases():
    context = {'player_class': 'Sorceress'}
    for base in ('Cedar Bow', 'Shadow Bow'):
        original = Item(base, 'unique', 'Kuko Shakaku', RAW, named_table_id=190)
        prepared = replace(
            original,
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem('Shael Rune'),),
            raw_stats=(*RAW, (93, 0, 20), (194, 0, 1)),
        )
        for label, item, ctx, truth, preparation in (
            ('shael', prepared, context, 'true', 'true'),
            ('known-no-ias', replace(original, complete=True), context, 'true', 'false'),
            ('unread-ias', original, context, 'true', 'unknown'),
            (
                'fervor-below-shael',
                replace(
                    prepared,
                    socket_items=(SocketItem('Jewel', ((93, 0, 15),), True),),
                    raw_stats=(*RAW, (93, 0, 15), (194, 0, 1)),
                ),
                context,
                'true',
                'false',
            ),
            ('wrong-class', prepared, {'player_class': 'Amazon'}, 'false', None),
            ('unknown-class', prepared, {}, 'unknown', None),
            ('ethereal-invalid', replace(prepared, ethereal=True), context, 'false', None),
            ('unknown-ethereal', replace(prepared, ethereal=None), context, 'unknown', None),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown', None),
            ('unidentified', replace(prepared, identified=False), context, 'false', None),
        ):
            role = {'id': ROLE, 'rule_trace': IsPartialDict(truth=truth)}
            active = truth == 'true' and preparation == 'true'
            if truth == 'true':
                role['dependencies'] = Contains(IsPartialDict(status=preparation))
            assessment = {'roles': Contains(IsPartialDict(**role))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(CONFIG))
                            for key in ('156:0', '158:0', '48:0', '49:0')
                        }
                    )
                )
            yield Case(
                id=f'enchant-kuko/{base}/{label}',
                item=item,
                context=ctx,
                covers=(ROLE,),
                scenario='unknown'
                if truth == 'unknown' or preparation == 'unknown'
                else 'positive'
                if active
                else 'negative',
                expected={
                    'assessment': IsPartialDict(**assessment),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '188:0', '107:27'), (CONFIG,)),
                report_contains=('Sockets: 1 — Shael',) if label == 'shael' else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/enchant-sorceress/variants/0/player/Weapon/0',
                    'third-parties/d2data/json/uniqueitems.json:/190',
                ),
            )


CASES = tuple(cases())
