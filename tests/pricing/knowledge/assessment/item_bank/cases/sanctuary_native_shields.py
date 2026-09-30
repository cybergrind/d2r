"""Sanctuary native rolls, base blocking and separately usable charges."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SLOW_MISSILES = (17 << 6) | 12
RAW = (
    (194, 0, 3),
    (20, 0, 40),
    (102, 0, 20),
    (99, 0, 20),
    (16, 0, 130),
    (32, 0, 250),
    (39, 0, 50),
    (41, 0, 50),
    (43, 0, 50),
    (45, 0, 50),
    (2, 0, 20),
    (35, 0, 7),
    (204, SLOW_MISSILES, (60 << 8) | 60),
)
KEYS = ('20:0', '102:0', '99:0', '16:0', '32:0', '39:0', '41:0', '43:0', '45:0', '2:0', '35:0')


def cases():
    for build, klass, slot in (('dragon-talon-assassin', 'Assassin', 2), ('lightning-strike-amazon', 'Amazon', 6)):
        role = build + '-player-sanctuary-off-hand-main-alternatives-support-word-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            original = NativeRunewordItem(
                'Troll Nest',
                quality,
                'Sanctuary',
                RAW,
                sockets=3,
                socket_contents='filled',
                runeword='Sanctuary',
                socket_items=tuple(SocketItem(n) for n in ('Ko Rune', 'Ko Rune', 'Mal Rune')),
            )
            variants = [
                ('minimum', original, context, 'true'),
                (
                    'maximum',
                    replace(
                        original,
                        raw_stats=tuple(
                            (s, p, 160 if s == 16 else 70 if s in (39, 41, 43, 45) else v) for s, p, v in RAW
                        ),
                    ),
                    context,
                    'true',
                ),
                (
                    'empty-charges',
                    replace(original, raw_stats=tuple((s, p, 60 << 8 if s == 204 else v) for s, p, v in RAW)),
                    context,
                    'true',
                ),
                ('ethereal-player', replace(original, ethereal=True), context, 'false'),
                ('wrong-class', original, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                ('unidentified', replace(original, identified=False), context, 'false'),
            ]
            for base in ('Tower Shield', 'Hyperion'):
                # Both native bases have24 blocking; Sanctuary adds20 to the captured total.
                variants.append(
                    (
                        base,
                        replace(original, base=base, raw_stats=tuple((s, p, 44 if s == 20 else v) for s, p, v in RAW)),
                        context,
                        'true',
                    )
                )
            for label, item, ctx, truth in variants:
                active = truth == 'true'
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if label == 'unidentified':
                    expected = {}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(config)) for k in KEYS})
                    )
                yield Case(
                    id=f'sanctuary-native/{build}/{quality}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else (config,),
                    absent_roles=(role,) if label == 'unidentified' else (),
                    absent_stat_configurations={f'204:{SLOW_MISSILES}': (config,)},
                    report_contains=(
                        'Sanctuary',
                        'Sockets: 3 — Ko, Ko, Mal',
                        'Slow Missiles',
                        '(130-175%)' if quality == 'superior' else '(130-160%)',
                        '(50-70%)',
                    )
                    if active
                    else (),
                    detail_contains=('Slow Missiles charges require separate use and are not assumed active.',)
                    if label == 'minimum'
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Off-Hand/{slot}',
                        'third-parties/d2data/json/runes.json:/Sanctuary',
                        'third-parties/d2data/json/armor.json:/ush,/tow,/urg',
                        'third-parties/d2data/json/skills.json:/17',
                    ),
                )


CASES = tuple(cases())
