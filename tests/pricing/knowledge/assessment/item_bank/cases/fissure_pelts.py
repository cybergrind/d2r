"""Fissure magic pelts: core skills, optional staffmods and independently verified jewels."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.caster_socketed_named import FIRE as DEFENDER
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLES = ('fissure-standard-pelt', 'fissure-magic-find-pelt')


def facet(damage=3, pierce=3):
    return SocketItem(
        'Jewel',
        ((329, 0, damage), (333, 0, pierce), (48, 0, 17), (49, 0, 45), (197, 3615, 100)),
        True,
        'Rainbow Facet',
        394,
    )


def pelt(damage=3, pierce=3, optional=3):
    return Item(
        'Dream Spirit',
        'magic',
        raw_stats=(
            (188, 42, 3),
            (107, 234, 3),
            (107, 250, optional),
            (107, 247, optional),
            (329, 0, damage + 5),
            (333, 0, pierce + 5),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled',
        socket_items=(DEFENDER, facet(damage, pierce)),
    )


def cases():
    original = pelt()
    ctx = {'player_class': 'Druid'}
    rows = [(f'facet-{a}-{b}', pelt(a, b), ctx, 'true', True) for a in (3, 5) for b in (3, 5)]
    rows += [
        ('antlers-base', replace(original, base='Antlers'), ctx, 'true', True),
        ('optional-one', pelt(optional=1), ctx, 'true', True),
        (
            'no-optional-staffmods',
            replace(original, raw_stats=tuple(s for s in original.raw_stats if s[1] not in (250, 247))),
            ctx,
            'true',
            True,
        ),
        (
            'low-elemental',
            replace(original, raw_stats=tuple((a, b, 2 if a == 188 else c) for a, b, c in original.raw_stats)),
            ctx,
            'false',
            False,
        ),
        (
            'low-fissure',
            replace(original, raw_stats=tuple((a, b, 2 if b == 234 else c) for a, b, c in original.raw_stats)),
            ctx,
            'false',
            False,
        ),
        ('wrong-class', original, {'player_class': 'Sorceress'}, 'false', False),
        ('unknown-class', original, {}, 'unknown', False),
        ('ethereal', replace(original, ethereal=True), ctx, 'false', False),
        ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown', False),
        ('unidentified', replace(original, identified=False), ctx, 'true', False),
        ('facet-above-native-maximum', replace(original, socket_items=(DEFENDER, facet(6, 3))), ctx, 'true', False),
        ('facet-below-minimum', replace(original, socket_items=(DEFENDER, facet(2, 3))), ctx, 'true', False),
        (
            'unread-facet',
            replace(original, socket_items=(DEFENDER, replace(facet(), raw_stats=(), complete=False))),
            ctx,
            'true',
            False,
        ),
        ('missing-defender', replace(original, socket_items=(SocketItem('Jewel'), facet())), ctx, 'true', False),
        (
            'owned-defender-not-socketed',
            replace(original, socket_items=(SocketItem('Jewel'), facet())),
            {**ctx, 'player_items': ["Defender's Fire"]},
            'true',
            False,
        ),
        ('parent-totals-only', replace(original, socket_items=(), socket_contents='unknown'), ctx, 'true', False),
        (
            'one-socket',
            replace(
                original,
                sockets=1,
                raw_stats=tuple((a, b, 1 if a == 194 else c) for a, b, c in original.raw_stats),
                socket_items=(DEFENDER,),
            ),
            ctx,
            'true',
            False,
        ),
        (
            'unsocketed',
            replace(
                original,
                sockets=0,
                socket_contents='empty',
                socket_items=(),
                raw_stats=tuple(s for s in original.raw_stats if s[0] not in (194, 329, 333)),
            ),
            ctx,
            'true',
            False,
        ),
    ]
    for label, item, context, truth, active in rows:
        expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in ROLES))}
        optional = {f'{a}:{b}' for a, b, _ in item.raw_stats} & {'107:250', '107:247'}
        if active:
            contributions = {
                k: IsPartialDict(
                    contributions=Contains(
                        *(
                            IsPartialDict(
                                configuration_id=r + '-stats',
                                role_id=r,
                                desirability='desirable',
                            )
                            for r in ROLES
                        )
                    )
                )
                for k in ('188:42', '107:234')
            }
            contributions.update(
                {
                    k: IsPartialDict(
                        contributions=Contains(
                            IsPartialDict(
                                configuration_id=ROLES[0] + '-stats',
                                role_id=ROLES[0],
                                desirability='supporting',
                            )
                        )
                    )
                    for k in optional
                }
            )
            expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(contributions))
        yield Case(
            id='fissure-pelts/' + label,
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=ROLES,
            scenario='positive'
            if active
            else 'unknown'
            if label.startswith(('unknown', 'unread', 'parent'))
            else 'negative',
            absent_configurations=() if active else tuple(r + '-stats' for r in ROLES),
            absent_stat_configurations=dict.fromkeys(('107:250', '107:247'), (ROLES[1] + '-stats',)),
            report_contains=('Fissure', '(1-3)', "Defender's Fire", 'Rainbow Facet', 'Sockets: 2') if active else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/fissure-druid/variants/1',
                'pricing/data/wp-a-builds.json:/fissure-druid/variants/2',
            ),
        )


CASES = tuple(cases())
