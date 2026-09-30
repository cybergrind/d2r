"""Existing Non-Ladder Mosaic claws require an equipped partner for this use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'dragon-talon-assassin-mosaic-off-hand-aura-recipe'
CONFIG = ROLE + '-stats'
RAW = (
    (188, 50, 2),
    (200, 0, 50),
    (93, 0, 20),
    (17, 0, 200),
    (18, 0, 200),
    (329, 0, 8),
    (330, 0, 8),
    (331, 0, 8),
    (60, 0, 7),
    (194, 0, 3),
)


def mosaic(quality):
    return NativeRunewordItem(
        'Greater Talons',
        quality,
        'Mosaic',
        RAW,
        sockets=3,
        socket_contents='filled',
        runeword='Mosaic',
        socket_items=tuple(SocketItem(r) for r in ('Mal Rune', 'Gul Rune', 'Amn Rune')),
    )


def cases():
    other = mosaic('normal')
    partner = normalize(other.capture()).to_dict()
    context = {'player_class': 'Assassin', 'player_equipment': {'weapon': partner}}
    for quality in ('normal', 'superior', 'low_quality'):
        original = mosaic(quality)
        variants = (
            ('minimum', original, context, 'true', 'true'),
            (
                'maximum',
                replace(
                    original,
                    raw_stats=tuple(
                        (s, p, 250 if s in (17, 18) else 15 if s in (329, 330, 331) else v) for s, p, v in RAW
                    ),
                ),
                context,
                'true',
                'true',
            ),
            ('elite-base', replace(original, base='Runic Talons'), context, 'true', 'true'),
            ('ethereal-offhand', replace(original, ethereal=True), context, 'false', 'true'),
            ('wrong-class', original, {**context, 'player_class': 'Necromancer'}, 'false', 'true'),
            ('unknown-class', original, {'player_equipment': context['player_equipment']}, 'unknown', 'true'),
            (
                'inventory-names-only',
                original,
                {'player_class': 'Assassin', 'player_items': ['Mosaic', 'Mosaic']},
                'true',
                'unknown',
            ),
            (
                'missing-partner',
                original,
                {'player_class': 'Assassin', 'player_equipment': {'weapon': None}},
                'true',
                'false',
            ),
            (
                'wrong-active-slot',
                original,
                {'player_class': 'Assassin', 'player_equipment': {'weapon_swap': partner}},
                'true',
                'unknown',
            ),
            (
                'ethereal-partner',
                original,
                {
                    'player_class': 'Assassin',
                    'player_equipment': {'weapon': normalize(replace(other, ethereal=True).capture()).to_dict()},
                },
                'true',
                'false',
            ),
        )
        for label, item, ctx, truth, companion in variants:
            active = truth == companion == 'true'
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=ROLE,
                        rule_trace=IsPartialDict(truth=truth),
                        dependencies=Contains(IsPartialDict(status=companion)),
                    )
                )
            }
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(CONFIG))
                            for key in ('188:50', '200:0', '329:0', '330:0', '331:0')
                        }
                    )
                )
            yield Case(
                id=f'mosaic-offhand/{quality}/{label}',
                item=item,
                context=ctx,
                covers=(ROLE,),
                scenario='positive' if active else 'unknown' if 'unknown' in (truth, companion) else 'negative',
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if active else (CONFIG,),
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0'), (CONFIG,)),
                report_contains=(
                    'Mosaic',
                    'Sockets: 3 — Mal, Gul, Amn',
                    '(8-15%)',
                    '(200-265%)' if quality == 'superior' else '(200-250%)',
                ),
                detail_contains=(
                    'One Mosaic has a 50% chance not to consume charges;',
                    'Weapon ED does not increase kick damage;',
                )
                if label == 'minimum'
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/dragon-talon-assassin/slots/Off-Hand/0',
                    'third-parties/d2data/json/runes.json:/Mosaic',
                ),
            )


CASES = tuple(cases())
