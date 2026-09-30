"""Measured Wrath fire casting, demon utility and native roll boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'fire-warlock-guide-measured-wrath-caster-remainder-alternative'
CONFIG = ROLE + '-stats'
BOUNDS = {
    (16, 0): (130, 180),
    (107, 376): (1, 3),
    (107, 394): (1, 3),
    (107, 398): (1, 3),
    (3, 0): (10, 20),
    (86, 0): (3, 5),
    **{(s, 0): (20, 30) for s in (39, 41, 43, 45)},
}
PRIORITIES = {
    '83:7': 'desirable',
    '105:0': 'desirable',
    '107:394': 'desirable',
    '107:398': 'desirable',
    '107:376': 'supporting',
    '3:0': 'supporting',
    '86:0': 'supporting',
    '16:0': 'supporting',
    **{f'{s}:0': 'desirable' for s in (39, 41, 43, 45)},
}
RAW = ((83, 7, 1), (105, 0, 25), (201, 25241, 5), *((s, p, lo) for (s, p), (lo, hi) in BOUNDS.items()))


def cases():
    ctx = {'player_class': 'Warlock'}
    for base in ('Burnt Text', 'Forgotten Volume'):
        original = Item(base, 'unique', 'Measured Wrath', RAW, named_table_id=411)
        rows = [
            ('minimum-rolls', original, ctx, 'true'),
            (
                'perfect-rolls',
                replace(
                    original, raw_stats=tuple((s, p, BOUNDS[s, p][1] if (s, p) in BOUNDS else v) for s, p, v in RAW)
                ),
                ctx,
                'true',
            ),
            ('ethereal', replace(original, ethereal=True), ctx, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
            ('unidentified', replace(original, identified=False), ctx, 'false'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unread-stats', replace(original, raw_stats=()), ctx, 'true'),
            ('empty-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), ctx, 'true'),
            (
                'unknown-filler',
                replace(original, sockets=1, socket_contents='unknown', raw_stats=(*RAW, (194, 0, 1))),
                ctx,
                'true',
            ),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown'),
            ('invalid-two-sockets', replace(original, sockets=2, raw_stats=(*RAW, (194, 0, 2))), ctx, 'false'),
        ]
        # All four resistances are one native roll; vary that group together.
        groups = [((s, p),) for s, p in BOUNDS if s not in (39, 41, 43, 45)] + [tuple((s, 0) for s in (39, 41, 43, 45))]
        for group in groups:
            rows.append(
                (
                    f'perfect-only-{group[0]}',
                    replace(
                        original,
                        raw_stats=tuple((s, p, BOUNDS[s, p][1] if (s, p) in group else v) for s, p, v in RAW),
                    ),
                    ctx,
                    'true',
                )
            )
        for key in PRIORITIES:
            stat, layer = map(int, key.split(':'))
            rows.append(
                (
                    'unread-' + key,
                    replace(original, raw_stats=tuple(s for s in RAW if s[:2] != (stat, layer))),
                    ctx,
                    'true',
                )
            )
        for label, item, context, truth in rows:
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
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            rolled = label in ('minimum-rolls', 'perfect-rolls') or label.startswith('perfect-only')
            if rolled:
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat={'id': s, 'layer': p, 'raw': v},
                                roll_quality='perfect' if v == BOUNDS[s, p][1] else 'low',
                            )
                            for s, p, v in item.raw_stats
                            if (s, p) in BOUNDS
                        )
                    )
                )
            yield Case(
                id=f'measured-wrath/{base}/{label}',
                item=item,
                context=context,
                expected=expected,
                covers=(ROLE,),
                scenario='unknown'
                if truth == 'unknown' or label.startswith('unread')
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations={
                    key: (CONFIG,) for key in (*PRIORITIES, '201:25241') if key not in captured or key == '201:25241'
                },
                report_contains=(
                    ('Measured Wrath', 'Trade tier:')
                    if item.identified and item.ethereal is False and label != 'invalid-two-sockets'
                    else ()
                )
                + (
                    (
                        '(130-180%)',
                        '(1-3) to Summon Tainted',
                        '(1-3) to Ring of Fire',
                        '(1-3) to Flame Wave',
                        '(10-20)',
                        '(3-5)',
                        '(20-30%)',
                    )
                    if rolled
                    else ()
                ),
                detail_contains=(
                    'not hard-point synergies',
                    'Summon Tainted is demon utility',
                    'not a guaranteed defensive or damage effect',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Off-Hand/4',
                    'third-parties/d2data/json/uniqueitems.json:/411',
                ),
            )


CASES = tuple(cases())
