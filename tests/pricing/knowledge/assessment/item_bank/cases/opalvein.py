"""Opalvein's six random damage choices do not all benefit Fire Warlock."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'fire-warlock-guide-opalvein-caster-utility-alternative'
CONFIG = ROLE + '-stats'
PRIORITIES = {
    '105:0': 'desirable',
    **{f'{s}:0': 'desirable' for s in (39, 41, 43, 45)},
    '86:0': 'supporting',
    '138:0': 'supporting',
    '329:0': 'desirable',
}
# The native property group picks exactly one property, not a sum of all six.
CHOICES = (
    ('magic', (357,), 3, 5),
    ('physical', (17, 18), 20, 40),
    ('fire', (329,), 3, 5),
    ('cold', (331,), 3, 5),
    ('lightning', (330,), 3, 5),
    ('poison', (332,), 3, 5),
)
RAW = ((105, 0, 10), (195, 25487, 2), (86, 0, 1), (138, 0, 1), *((s, 0, 6) for s in (39, 41, 43, 45)))


def cases():
    ctx = {'player_class': 'Warlock'}
    original = Item('Ring', 'unique', 'Opalvein', (*RAW, (329, 0, 3)), named_table_id=416)
    rows = [
        (f'{name}-{value}', replace(original, raw_stats=(*RAW, *((s, 0, value) for s in stats))), ctx, 'true')
        for name, stats, lo, hi in CHOICES
        for value in (lo, hi)
    ]
    rows += [
        (
            f'complete-{name}-{value}',
            replace(original, complete=True, raw_stats=(*RAW, *((s, 0, value) for s in stats))),
            ctx,
            'true',
        )
        for name, stats, lo, hi in CHOICES
        for value in (lo, hi)
    ]
    rows += [
        ('unread-random-choice', replace(original, raw_stats=RAW), ctx, 'true'),
        ('ethereal-invalid', replace(original, ethereal=True), ctx, 'false'),
        ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
        ('unidentified', replace(original, identified=False), ctx, 'false'),
        ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', original, {}, 'unknown'),
        ('unread-stats', replace(original, raw_stats=()), ctx, 'true'),
        ('invalid-socket', replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))), ctx, 'false'),
        ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown'),
    ]
    for key in PRIORITIES:
        stat, layer = map(int, key.split(':'))
        rows.append(
            (
                'unread-' + key,
                replace(original, raw_stats=tuple(s for s in original.raw_stats if s[:2] != (stat, layer))),
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
        range_text = ()
        if any(label.startswith(prefix + name + '-') for name, *_ in CHOICES for prefix in ('', 'complete-')):
            range_text = ('(20-40%)',) if 'physical-' in label else ('(3-5%)',)
        yield Case(
            id='opalvein/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario='unknown'
            if truth == 'unknown' or label.startswith('unread')
            else 'positive'
            if active
            else 'negative',
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations={
                key: (CONFIG,)
                for key in (*PRIORITIES, '357:0', '17:0', '18:0', '330:0', '331:0', '332:0', '195:25487')
                if key not in captured or key not in PRIORITIES
            },
            report_contains=('Opalvein', 'Trade tier:', *range_text)
            if item.identified and item.ethereal is False and item.sockets == 0
            else (),
            detail_contains=(
                'require wearer kill credit',
                'Only an observed Fire Skill Damage modifier',
                'Flame Wave on attack is not triggered by every spell cast',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/Rings/2',
                'third-parties/d2data/json/uniqueitems.json:/416',
                'third-parties/d2data/json/skills.json:/398',
                'third-parties/d2data/json/propertygroups.json:/magdam-rand',
            ),
        )


CASES = tuple(cases())
