"""Six linked Lems establish a gold-find payload; an observed total alone cannot."""

from dataclasses import replace
from itertools import product

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'gold-find-standard-off-hand-lem-sword'
USES = (
    ('war-cry', 2, 'weapon-swap', 'Weapon-Swap'),
    ('war-cry', 2, 'off-hand-swap', 'Off-Hand-Swap'),
    ('whirlwind', 3, 'weapon-swap', 'Weapon-Swap'),
    ('whirlwind', 3, 'off-hand-swap', 'Off-Hand-Swap'),
    ('leap-only', 4, 'weapon', 'Weapon'),
    ('leap-only', 4, 'off-hand', 'Off-Hand'),
)
SPECIALIST_ROLES = tuple(f'gold-find-{variant}-{slot}-lem-sword' for variant, _, slot, _ in USES)
LEMS = tuple(SocketItem('Lem Rune') for _ in range(6))


def cases():
    for group, quality in product(('standard', 'specialist'), ('normal', 'superior')):
        roles = (ROLE,) if group == 'standard' else SPECIALIST_ROLES
        configs = tuple(role + '-stats' for role in roles)
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
            (
                'phase',
                replace(original, base='Phase Blade'),
                context,
                'true' if group == 'standard' else 'false',
                'true',
                group == 'standard',
            ),
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
                    *(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(IsPartialDict(status=linked)),
                        )
                        for role in roles
                    )
                )
            }
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            '79:0': IsPartialDict(
                                contributions=Contains(
                                    *(
                                        IsPartialDict(
                                            configuration_id=role + '-stats',
                                            role_id=role,
                                            desirability='desirable',
                                        )
                                        for role in roles
                                    )
                                )
                            )
                        }
                    )
                )
            yield Case(
                id=f'gold-find-lem-sword/{group}/{quality}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=roles,
                scenario='positive'
                if active
                else 'unknown'
                if 'unknown' in (truth, linked) or label == 'uncaptured-gold'
                else 'negative',
                absent_configurations=() if active else configs,
                report_contains=('Sockets: 6', 'Lem', '450% Extra Gold') if active else (),
                report_absent=('Lem Rune',),
                detail_contains=('Ethereal swords cannot be repaired;',)
                if group == 'specialist' and label == 'ethereal-crystal'
                else (),
                evidence=('pricing/data/wp-a-builds.json:/gold-find-barbarian/variants/1/player/Off-Hand/0',)
                if group == 'standard'
                else tuple(
                    f'pricing/data/wp-a-builds.json:/gold-find-barbarian/variants/{index}/player/{slot}/0'
                    for _, index, _, slot in USES
                ),
            )


CASES = tuple(cases())
