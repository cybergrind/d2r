"""Echoing Strike's documented Silence/Void alternatives retain distinct mechanics."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


DECREPIFY = (87 << 6) | 4
SILENCE = (
    (127, 0, 2),
    (17, 0, 200),
    (18, 0, 200),
    (62, 0, 11),
    (93, 0, 20),
    (99, 0, 20),
    (39, 0, 75),
    (41, 0, 75),
    (43, 0, 75),
    (45, 0, 75),
    (80, 0, 30),
    (138, 0, 2),
    (122, 0, 75),
    (124, 0, 50),
    (112, 0, 32),
    (113, 0, 33),
    (194, 0, 6),
)
VOID = (
    (127, 0, 2),
    (105, 0, 40),
    (357, 0, 10),
    (97, 402, 1),
    (0, 0, 8),
    (1, 0, 8),
    (2, 0, 8),
    (3, 0, 8),
    (80, 0, 30),
    (152, 0, 1),
    (204, DECREPIFY, (35 << 8) | 35),
    (194, 0, 3),
)


def cases():
    context = {'player_class': 'Warlock'}
    for name, base, other_base, raw, runes, keys, ignored, index in (
        (
            'Silence',
            'Berserker Axe',
            'Colossus Blade',
            SILENCE,
            ('Dol Rune', 'Eld Rune', 'Hel Rune', 'Ist Rune', 'Tir Rune', 'Vex Rune'),
            (
                '127:0',
                '17:0',
                '18:0',
                '62:0',
                '99:0',
                '39:0',
                '41:0',
                '43:0',
                '45:0',
                '80:0',
                '138:0',
                '122:0',
                '124:0',
            ),
            ('93:0', '112:0', '113:0'),
            5,
        ),
        (
            'Void',
            'Legend Spike',
            'Fanged Knife',
            VOID,
            ('Thul Rune', 'Zod Rune', 'Ist Rune'),
            ('127:0', '105:0', '357:0', '0:0', '1:0', '2:0', '3:0', '80:0'),
            (f'204:{DECREPIFY}',),
            0,
        ),
    ):
        role = f'echoing-strike-warlock-guide-player-{name.lower()}-weapon-main-alternatives-caster-word-remainder'
        config = role + '-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            original = NativeRunewordItem(
                base,
                quality,
                name,
                raw,
                sockets=len(runes),
                socket_contents='filled',
                runeword=name,
                socket_items=tuple(SocketItem(r) for r in runes),
            )
            variants = [
                ('native', original, context, 'true'),
                ('other-legal-base', replace(original, base=other_base), context, 'true'),
                ('ethereal', replace(original, ethereal=True), context, 'true'),
                ('wrong-class', original, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
            ]
            if name == 'Void':
                variants.extend(
                    [
                        (
                            'maximum-rolls',
                            replace(
                                original,
                                raw_stats=tuple(
                                    (s, p, 15 if s == 357 else 3 if s == 97 else 12 if s in (0, 1, 2, 3) else v)
                                    for s, p, v in raw
                                ),
                            ),
                            context,
                            'true',
                        ),
                        (
                            'exhausted-decrepify',
                            replace(original, raw_stats=tuple((s, p, 35 << 8 if s == 204 else v) for s, p, v in raw)),
                            context,
                            'true',
                        ),
                    ]
                )
            elif quality == 'superior':
                variants.append(
                    (
                        'superior-enhancement',
                        replace(original, raw_stats=tuple((s, p, 215 if s in (17, 18) else v) for s, p, v in raw)),
                        context,
                        'true',
                    )
                )
            for label, item, ctx, truth in variants:
                active = truth == 'true'
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                report = (
                    (
                        'Silence',
                        'Sockets: 6 — Dol, Eld, Hel, Ist, Tir, Vex',
                        '11% Mana stolen per hit',
                        'Hit Blinds Target',
                        'Hit Causes Monster to Flee',
                    )
                    if name == 'Silence'
                    else (
                        'Void',
                        'Sockets: 3 — Thul, Zod, Ist',
                        'Abyss',
                        'Decrepify',
                        'Indestructible',
                        '(10-15%)',
                        '(8-12)',
                        '(1-3)',
                    )
                )
                yield Case(
                    id=f'warlock-native-weapons/{name}/{quality}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(ignored, (config,)),
                    report_contains=report,
                    detail_contains=(
                        ('Echoing Strike uses FCR, not IAS.',)
                        if name == 'Silence'
                        else (
                            'it does not multiply physical Echoing damage.',
                            'Decrepify requires casting available charges and is not a passive aura.',
                        )
                    )
                    if label == 'native'
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/slots/Weapon/{index}',
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )


CASES = tuple(cases())
