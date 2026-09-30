"""Warlock casting utility is distinct from slow-on-hit and melee durability."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'echoing-strike-warlock-guide-bloodpact-shard-caster-remainder-alternative'
CONFIG = ROLE + '-stats'
BOUNDS = {(76, 0): (10, 15), (107, 378): (2, 3), (107, 380): (2, 3), (107, 382): (1, 3), (80, 0): (20, 35)}
PRIORITIES = {
    '127:0': 'desirable',
    '105:0': 'desirable',
    '76:0': 'desirable',
    '107:378': 'supporting',
    '107:380': 'supporting',
    '107:382': 'supporting',
    '80:0': 'supporting',
}
RAW = ((127, 0, 1), (105, 0, 30), (150, 0, 25), *((s, p, lo) for (s, p), (lo, hi) in BOUNDS.items()))


def cases():
    ctx = {'player_class': 'Warlock'}
    original = Item('Mithral Point', 'unique', 'Bloodpact Shard', RAW, named_table_id=414)
    perfect = replace(original, raw_stats=tuple((s, p, BOUNDS[s, p][1] if (s, p) in BOUNDS else v) for s, p, v in RAW))
    rows = [
        ('minimum-rolls', original, ctx, 'true'),
        ('perfect-rolls', perfect, ctx, 'true'),
        ('ethereal-casting', replace(original, ethereal=True), ctx, 'true'),
        ('unknown-ethereal', replace(original, ethereal=None), ctx, 'true'),
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
    for key in PRIORITIES:
        stat, layer = map(int, key.split(':'))
        rows.append(
            ('unread-' + key, replace(original, raw_stats=tuple(s for s in RAW if s[:2] != (stat, layer))), ctx, 'true')
        )
    for stat, layer in BOUNDS:
        rows.append(
            (
                f'perfect-only-{stat}:{layer}',
                replace(
                    original,
                    raw_stats=tuple((s, p, BOUNDS[s, p][1] if (s, p) == (stat, layer) else v) for s, p, v in RAW),
                ),
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
        if label in ('minimum-rolls', 'perfect-rolls') or label.startswith('perfect-only'):
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
            id='bloodpact-shard/' + label,
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
                key: (CONFIG,) for key in (*PRIORITIES, '150:0') if key not in captured or key == '150:0'
            },
            report_contains=(
                ('Bloodpact Shard', 'Trade tier:')
                if item.identified and item.ethereal is False and label != 'invalid-two-sockets'
                else ()
            )
            + (
                ('(10-15%)', '(2-3) to Blood Oath', '(2-3) to Blood Boil', '(1-3) to Bind Demon', '(20-35%)')
                if label in ('minimum-rolls', 'perfect-rolls') or label.startswith('perfect-only')
                else ()
            ),
            detail_contains=(
                'Slows Target is not applied by Echoing Strike',
                'does not establish safe melee durability',
                'not hard-point synergies',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/9',
                'third-parties/d2data/json/uniqueitems.json:/414',
            ),
        )


CASES = tuple(cases())
