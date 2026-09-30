"""Native Harmony movement swaps: aura utility is separate from attack rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


USES = (
    ('double-throw-barbarian-guide', 'Barbarian', 7),
    ('fissure-druid', 'Druid', 4),
    ('lightning-fury-amazon-guide', 'Amazon', 4),
    ('lightning-sorceress', 'Sorceress', 5),
    ('lightning-strike-amazon', 'Amazon', 4),
    ('poison-nova-necromancer', 'Necromancer', 3),
)
# Native runes/Harmony: fixed level10 Vigor and 200-275 ED. Partial capture;
# unused elemental damage, Valkyrie and Revive charges are deliberately not fabricated.
RAW = ((151, 115, 10), (17, 0, 200), (18, 0, 200), (27, 0, 20), (2, 0, 10), (194, 0, 4))


def cases():
    for build, klass, slot in USES:
        role = build + '-player-harmony-weapon-swap-main-alternatives-word-utility-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            original = NativeRunewordItem(
                'Blade Bow',
                quality,
                'Harmony',
                RAW,
                sockets=4,
                socket_contents='filled',
                runeword='Harmony',
                socket_items=tuple(SocketItem(name) for name in ('Tir Rune', 'Ith Rune', 'Sol Rune', 'Ko Rune')),
            )
            no_aura = tuple(row for row in RAW if row[0] != 151)
            for label, item, ctx, truth, aura in (
                ('native', original, context, 'true', True),
                ('crossbow', replace(original, base='Colossus Crossbow'), context, 'true', True),
                (
                    'maximum-recipe-ed',
                    replace(original, raw_stats=tuple((s, p, 275 if s in (17, 18) else v) for s, p, v in RAW)),
                    context,
                    'true',
                    True,
                ),
                ('wrong-class', original, {'player_class': 'Paladin'}, 'false', False),
                ('unknown-class', original, {}, 'unknown', False),
                ('unread-aura', replace(original, raw_stats=no_aura), context, 'true', False),
                ('known-no-aura', replace(original, raw_stats=no_aura, complete=True), context, 'true', False),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if aura:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict({'151:115': IsPartialDict(configuration_ids=Contains(config))})
                    )
                yield Case(
                    id=f'harmony-movement/{build}/{quality}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    scenario='unknown'
                    if label == 'unread-aura' or truth == 'unknown'
                    else 'positive'
                    if aura
                    else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if aura else (config,),
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '27:0', '2:0'), (config,)),
                    report_contains=('Harmony', 'Sockets: 4 — Tir, Ith, Sol, Ko'),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon-Swap/{slot}',
                        'third-parties/d2data/json/runes.json:/Harmony',
                        'third-parties/d2data/json/weapons.json:/6hb,/6hx',
                    ),
                )


CASES = tuple(cases())
