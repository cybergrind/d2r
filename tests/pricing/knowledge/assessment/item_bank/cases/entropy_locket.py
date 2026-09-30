"""Entropy Locket distinguishes Warlock magic utility from Nova lightning."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = {
    'Warlock': 'echoing-strike-warlock-guide-entropy-locket-caster-utility-alternative',
    'Sorceress': 'nova-sorceress-guide-entropy-locket-caster-utility-alternative',
}
BOUNDS = {357: (5, 10), 105: (5, 10), 41: (25, 40), 77: (10, 15), 35: (8, 12)}
PRIORITIES = {'105:0': 'desirable', '41:0': 'supporting', '77:0': 'desirable', '35:0': 'supporting'}
RAW = (*((s, 0, lo) for s, (lo, hi) in BOUNDS.items()), (198, 25555, 4))


def cases():
    original = Item('Amulet', 'unique', 'Entropy Locket', RAW, named_table_id=417)
    for klass, role in ROLES.items():
        source = (
            'echoing-strike-warlock-guide/slots/Amulets/2'
            if klass == 'Warlock'
            else 'nova-sorceress-guide/slots/Amulets/3'
        )
        ctx = {'player_class': klass}
        config = role + '-stats'
        priorities = PRIORITIES | ({'357:0': 'desirable'} if klass == 'Warlock' else {})
        rows = [
            ('minimum-rolls', original, ctx, 'true'),
            (
                'perfect-rolls',
                replace(original, raw_stats=tuple((s, p, BOUNDS[s][1] if s in BOUNDS else v) for s, p, v in RAW)),
                ctx,
                'true',
            ),
            ('ethereal-invalid', replace(original, ethereal=True), ctx, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
            ('unidentified', replace(original, identified=False), ctx, 'false'),
            ('wrong-class', original, {'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unread-stats', replace(original, raw_stats=()), ctx, 'true'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown'),
            ('invalid-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), ctx, 'false'),
        ]
        for stat in BOUNDS:
            rows.append(
                (
                    f'perfect-only-{stat}',
                    replace(original, raw_stats=tuple((s, p, BOUNDS[s][1] if s == stat else v) for s, p, v in RAW)),
                    ctx,
                    'true',
                )
            )
            rows.append(
                (f'unread-{stat}', replace(original, raw_stats=tuple(s for s in RAW if s[0] != stat)), ctx, 'true')
            )
        for label, item, context, truth in rows:
            active = truth == 'true'
            captured = {f'{s}:{p}' for s, p, _ in item.raw_stats}
            assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(configuration_id=config, role_id=role, desirability=grade)
                                )
                            )
                            for key, grade in priorities.items()
                            if key in captured
                        }
                    )
                )
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            rolled = label in ('minimum-rolls', 'perfect-rolls') or label.startswith('perfect-only')
            if rolled:
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat={'id': s, 'layer': p, 'raw': v},
                                roll_quality='perfect' if v == BOUNDS[s][1] else 'low',
                            )
                            for s, p, v in item.raw_stats
                            if s in BOUNDS
                        )
                    )
                )
            yield Case(
                id=f'entropy-locket/{klass}/{label}',
                item=item,
                context=context,
                expected=expected,
                covers=(role,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (config,),
                absent_stat_configurations={
                    key: (config,)
                    for key in (*priorities, '198:25555', *(('357:0',) if klass == 'Sorceress' else ()))
                    if key not in captured or key == '198:25555' or (key == '357:0' and klass == 'Sorceress')
                },
                report_contains=(
                    ('Entropy Locket', 'Trade tier:')
                    if item.identified and item.ethereal is False and item.sockets == 0
                    else ()
                )
                + (('(5-10%)', '(25-40%)', '(10-15%)', '(8-12)') if rolled else ()),
                detail_contains=(
                    'not the physical echoes themselves',
                    'does not multiply Nova lightning damage',
                    'on-striking event, which Echoing Strike cannot trigger',
                )
                if active
                else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/417',
                    f'pricing/data/wp-a-builds.json:/{source}',
                ),
            )


CASES = tuple(cases())
