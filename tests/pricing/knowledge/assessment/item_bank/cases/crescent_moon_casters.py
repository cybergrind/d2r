"""Native Crescent Moon: caster resistance piercing is distinct from attack effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


USES = (
    ('lightning-sentry-assassin', 'Assassin', 'weapon', 'Weapon', 2),
    ('lightning-sentry-assassin', 'Assassin', 'weapon-swap', 'Weapon-Swap', 1),
    ('lightning-sorceress', 'Sorceress', 'weapon', 'Weapon', 3),
    ('nova-sorceress-guide', 'Sorceress', 'weapon', 'Weapon', 1),
)
# Native recipe: 35 enemy lightning pierce, 180-220 ED, 9-11 magic absorb.
# Shael/Um/Tir contribute 20 IAS, 25 open wounds, and 2 mana after each kill.
# Partial capture deliberately omits charges/procs, rather than inventing activation.
RAW = (
    (334, 0, 35),
    (17, 0, 180),
    (18, 0, 180),
    (147, 0, 9),
    (115, 0, 1),
    (93, 0, 20),
    (135, 0, 25),
    (138, 0, 2),
    (194, 0, 3),
)


def cases():
    for build, klass, slot_id, slot, index in USES:
        role = build + '-player-crescent moon-' + slot_id + '-main-alternatives-caster-word-remainder'
        config = role + '-stats'
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            original = NativeRunewordItem(
                'Crystal Sword',
                quality,
                'Crescent Moon',
                RAW,
                sockets=3,
                socket_contents='filled',
                runeword='Crescent Moon',
                socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Um Rune', 'Tir Rune')),
            )
            missing = tuple(row for row in RAW if row[0] != 334)
            for label, item, ctx, truth, pierce in (
                ('native-minimum', original, context, 'true', True),
                (
                    'maximum-rolls',
                    replace(
                        original,
                        raw_stats=tuple((s, p, 220 if s in (17, 18) else 11 if s == 147 else v) for s, p, v in RAW),
                    ),
                    context,
                    'true',
                    True,
                ),
                ('phase-blade', replace(original, base='Phase Blade'), context, 'true', True),
                ('ethereal-caster', replace(original, ethereal=True), context, 'true', True),
                ('wrong-class', original, {'player_class': 'Druid'}, 'false', False),
                ('unknown-class', original, {}, 'unknown', False),
                ('unread-pierce', replace(original, raw_stats=missing), context, 'true', False),
                ('known-no-pierce', replace(original, raw_stats=missing, complete=True), context, 'true', False),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                keys = ['147:0', '138:0']
                if klass == 'Assassin':
                    keys.append('93:0')
                if pierce:
                    keys.append('334:0')
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                excluded = ['17:0', '18:0', '115:0', '135:0']
                if klass == 'Sorceress':
                    excluded.append('93:0')
                if not pierce:
                    excluded.append('334:0')
                yield Case(
                    id=f'crescent-moon-casters/{build}/{slot_id}/{quality}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='unknown'
                    if truth == 'unknown' or label == 'unread-pierce'
                    else 'negative'
                    if truth == 'false' or label == 'known-no-pierce'
                    else 'positive',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=(
                        'Crescent Moon',
                        'Sockets: 3 — Shael, Um, Tir',
                        '(180-235%)' if quality == 'superior' else '(180-220%)',
                        '(9-11)',
                    ),
                    detail_contains=(
                        'Attack procs, weapon ED and Ignore Target Defense are not spell or trap damage multipliers.',
                    )
                    if label == 'native-minimum'
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/{slot}/{index}',
                        'third-parties/d2data/json/runes.json:/Crescent Moon',
                    ),
                )


CASES = tuple(cases())
