"""Six linked Lems establish a gold-find payload; an observed total alone cannot."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'gold-find-standard-off-hand-lem-sword'
CONFIG = ROLE + '-stats'
LEMS = tuple(SocketItem('Lem Rune') for _ in range(6))


def cases():
    for quality in ('normal', 'superior'):
        original = Item(
            'Crystal Sword',
            quality,
            raw_stats=((79, 0, 450), (194, 0, 6)),
            sockets=6,
            socket_contents='filled',
            socket_items=LEMS,
        )
        context = {'player_class': 'Barbarian'}
        examples = (
            ('crystal', original, context, 'true', 'true', True),
            ('phase', replace(original, base='Phase Blade'), context, 'true', 'true', True),
            ('ethereal-crystal', replace(original, ethereal=True), context, 'true', 'true', True),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'true', 'true', True),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false', 'true', False),
            ('unknown-class', original, {}, 'unknown', 'true', False),
            ('wrong-base', replace(original, base='War Sword'), context, 'false', 'true', False),
            (
                'five-sockets',
                replace(original, sockets=5, raw_stats=((79, 0, 375), (194, 0, 5)), socket_items=LEMS[:5]),
                context,
                'false',
                'false',
                False,
            ),
            (
                'wrong-rune',
                replace(original, socket_items=(*LEMS[:5], SocketItem('Ist Rune'))),
                context,
                'true',
                'false',
                False,
            ),
            ('partial-children', replace(original, socket_items=LEMS[:5]), context, 'true', 'unknown', False),
            (
                'total-without-links',
                replace(original, socket_items=(), socket_contents='unknown'),
                context,
                'true',
                'unknown',
                False,
            ),
            (
                'six-empty',
                replace(original, raw_stats=(), socket_items=(), socket_contents='empty'),
                context,
                'true',
                'false',
                False,
            ),
            (
                'unprepared',
                replace(original, raw_stats=(), sockets=0, socket_items=(), socket_contents='empty'),
                context,
                'true',
                'false',
                False,
            ),
            ('uncaptured-gold', replace(original, raw_stats=((194, 0, 6),)), context, 'true', 'true', False),
            (
                'inconsistent-gold',
                replace(original, raw_stats=((79, 0, 449), (194, 0, 6))),
                context,
                'true',
                'true',
                False,
            ),
            ('unidentified', replace(original, identified=False), context, 'false', 'true', False),
        )
        for label, item, loadout, truth, linked, active in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=ROLE,
                        rule_trace=IsPartialDict(truth=truth),
                        dependencies=Contains(IsPartialDict(status=linked)),
                    )
                )
            }
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            '79:0': IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(
                                        configuration_id=CONFIG,
                                        role_id=ROLE,
                                        desirability='desirable',
                                    )
                                )
                            )
                        }
                    )
                )
            yield Case(
                id=f'gold-find-lem-sword/{quality}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario='positive'
                if active
                else 'unknown'
                if 'unknown' in (truth, linked) or label == 'uncaptured-gold'
                else 'negative',
                absent_configurations=() if active else (CONFIG,),
                report_contains=('Sockets: 6', 'Lem', '450% Extra Gold') if active else (),
                report_absent=('Lem Rune',),
                evidence=('pricing/data/wp-a-builds.json:/gold-find-barbarian/variants/1/player/Off-Hand/0',),
            )


CASES = tuple(cases())
