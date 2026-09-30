"""Ring-local combinations and independently captured farming loadout prerequisites."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


TAL = ["Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication"]


def emit(role, label, item, context, truth, active, priorities):
    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
    captured = {f'{a}:{b}' for a, b, _ in item.raw_stats}
    if active:
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict(
                {
                    key: IsPartialDict(
                        contributions=Contains(
                            IsPartialDict(
                                configuration_id=role + '-stats',
                                role_id=role,
                                desirability=grade,
                            )
                        )
                    )
                    for key, grade in priorities.items()
                    if key in captured
                }
            )
        )
    return Case(
        id=f'sorceress-endgame-rings/{role}/{label}',
        item=item,
        context=context,
        expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
        covers=(role,),
        scenario='positive'
        if active
        else 'unknown'
        if truth == 'unknown' or label.startswith('unknown')
        else 'negative',
        absent_configurations=() if active else (role + '-stats',),
        absent_stat_configurations={k: (role + '-stats',) for k in priorities if k not in captured},
        report_contains=('Ring',) if active else (),
        evidence=('pricing/data/wp-a-builds.json',),
    )


def farming():
    for role, quality, breakpoint in (
        ('meteor-mf-rare-ring', 'rare', 105),
        ('lightning-mf-magic-ring', 'magic', 117),
    ):
        stats = ((80, 0, 5),)
        if quality == 'rare':
            stats += ((105, 0, 10), (7, 0, 20 * 256), (39, 0, 11), (41, 0, 11), (43, 0, 11), (45, 0, 11))
        original = Item('Ring', quality, raw_stats=stats)
        context = {
            'player_class': 'Sorceress',
            'player_total_fcr': breakpoint,
            'player_total_fhr': 60,
            'player_items': TAL,
        }
        priorities = {'80:0': 'desirable'}
        if quality == 'rare':
            priorities.update(
                {'105:0': 'desirable', **dict.fromkeys(('7:0', '39:0', '41:0', '43:0', '45:0'), 'supporting')}
            )
        rows = [
            ('modest-rolls', original, context, 'true', True),
            (
                'target-mf',
                replace(
                    original,
                    raw_stats=tuple(
                        (a, b, 25 if quality == 'rare' else 40) if a == 80 else (a, b, c) for a, b, c in stats
                    ),
                ),
                context,
                'true',
                True,
            ),
            ('no-mf', replace(original, raw_stats=tuple(s for s in stats if s[0] != 80)), context, 'unknown', False),
            ('wrong-class', original, {**context, 'player_class': 'Barbarian'}, 'false', False),
            ('unknown-class', original, {**context, 'player_class': None}, 'unknown', False),
            ('below-fcr', original, {**context, 'player_total_fcr': breakpoint - 1}, 'false', False),
            ('unknown-fcr', original, {**context, 'player_total_fcr': None}, 'unknown', False),
            ('unknown-equipment', original, {**context, 'player_items': None}, 'true', False),
            ('ethereal-invalid', replace(original, ethereal=True), context, 'false', False),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown', False),
            ('unidentified', replace(original, identified=False), context, 'false', False),
        ]
        for piece in TAL:
            rows.append(
                (
                    'missing-' + piece,
                    original,
                    {**context, 'player_items': [x for x in TAL if x != piece]},
                    'true',
                    False,
                )
            )
        if quality == 'rare':
            rows += [
                (
                    'no-ring-fcr',
                    replace(original, raw_stats=tuple(s for s in stats if s[0] != 105)),
                    context,
                    'unknown',
                    False,
                ),
                ('below-fhr', original, {**context, 'player_total_fhr': 59}, 'false', False),
                ('unknown-fhr', original, {**context, 'player_total_fhr': None}, 'unknown', False),
            ]
        for label, item, ctx, truth, active in rows:
            yield emit(role, label, item, ctx, truth, active, priorities)


def ubers():
    role = 'lightning-ubers-ring'
    original = Item('Ring', 'rare', raw_stats=((105, 0, 10), (41, 0, 10)))
    context = {'player_class': 'Sorceress'}
    priorities = {
        '105:0': 'desirable',
        **dict.fromkeys(('41:0', '0:0', '7:0', '9:0', '39:0', '43:0', '45:0'), 'supporting'),
    }
    maximum = replace(
        original,
        raw_stats=(
            (105, 0, 10),
            (41, 0, 41),
            (0, 0, 20),
            (7, 0, 40 * 256),
            (9, 0, 90 * 256),
            (39, 0, 11),
            (43, 0, 11),
            (45, 0, 11),
        ),
    )
    for label, item, truth, active in (
        ('core', original, 'true', False),
        ('planner-rolls', maximum, 'true', False),
        ('no-lightning-resist', replace(original, raw_stats=((105, 0, 10),)), 'unknown', False),
        ('no-fcr', replace(original, raw_stats=((41, 0, 41),)), 'unknown', False),
        ('fire-not-lightning', replace(original, raw_stats=((105, 0, 10), (39, 0, 41))), 'unknown', False),
        ('ethereal-invalid', replace(original, ethereal=True), 'false', False),
        ('unknown-ethereal', replace(original, ethereal=None), 'unknown', False),
        ('unidentified', replace(original, identified=False), 'true', False),
    ):
        case = emit(role, label, item, context, truth, active, priorities)
        if label in ('core', 'planner-rolls'):
            case = replace(
                case,
                scenario='positive',
                expected={
                    **case.expected,
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                status='partial',
                                rule_trace=IsPartialDict(truth='true'),
                                missing=Contains(
                                    'Uber setup assumes stacked lightning resistance, Thundergod\u2019s Vigor '
                                    'and Treachery Fade prebuff; this ring alone does not establish survival.'
                                ),
                            )
                        )
                    ),
                },
            )
        yield case


CASES = (*farming(), *ubers())
