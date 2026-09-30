"""Enchant delivery stays separate from Demon Machine's physical weapon damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'enchant-sorceress-demon-machine-main-alternatives-delivery-weapon'
CONFIG = ROLE + '-stats'
RAW = ((156, 0, 66), (158, 0, 6), (19, 0, 632), (9, 0, 36 * 256), (31, 0, 321), (17, 0, 123), (18, 0, 123))
PRIORITIES = {
    '156:0': 'desirable',
    '158:0': 'desirable',
    '19:0': 'supporting',
    '9:0': 'supporting',
    '31:0': 'supporting',
}


def cases():
    context = {'player_class': 'Sorceress'}
    for base in ('Chu-Ko-Nu', 'Demon Crossbow'):
        original = Item(base, 'unique', 'Demon Machine', RAW, named_table_id=199)
        rows = [
            ('native-delivery', original, context, 'true'),
            ('ethereal-invalid', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unread-stats', replace(original, raw_stats=()), context, 'true'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('empty-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'true'),
            (
                'unknown-filler',
                replace(original, sockets=1, socket_contents='unknown', raw_stats=(*RAW, (194, 0, 1))),
                context,
                'true',
            ),
            (
                'shael-socket',
                replace(
                    original,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem('Shael Rune'),),
                    raw_stats=(*RAW, (194, 0, 1), (93, 0, 20)),
                ),
                context,
                'true',
            ),
            ('invalid-two-sockets', replace(original, sockets=2, raw_stats=(*RAW, (194, 0, 2))), context, 'false'),
        ]
        for key in PRIORITIES:
            stat, layer = map(int, key.split(':'))
            rows.append(
                (
                    'unread-' + key,
                    replace(original, raw_stats=tuple(s for s in RAW if s[:2] != (stat, layer))),
                    context,
                    'true',
                )
            )
        for label, item, loadout, truth in rows:
            active = truth == 'true'
            captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
            assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability=grade)
                                )
                            )
                            for key, grade in PRIORITIES.items()
                            if key in captured
                        }
                    )
                )
            yield Case(
                id=f'enchant-demon-machine/{base}/{label}',
                item=item,
                context=loadout,
                expected={
                    'assessment': IsPartialDict(**assessment),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=(ROLE,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations={
                    key: (CONFIG,)
                    for key in (*PRIORITIES, '17:0', '18:0')
                    if key not in captured or key in ('17:0', '18:0')
                },
                report_contains=(
                    ('Demon Machine', 'Trade tier:')
                    if item.identified and item.ethereal is False and label != 'invalid-two-sockets'
                    else ()
                )
                + (('+36 to Mana',) if item.identified and '9:0' in captured else ())
                + (('Sockets: 1 — Shael',) if label == 'shael-socket' else ()),
                detail_contains=(
                    'Upgrading physical base damage does not multiply Enchant fire damage',
                    'Explosive bolts and pierce provide delivery',
                    'Check the full attack-speed setup',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/enchant-sorceress/slots/Weapon/0',
                    'third-parties/d2data/json/uniqueitems.json:/199',
                ),
            )


CASES = tuple(cases())
