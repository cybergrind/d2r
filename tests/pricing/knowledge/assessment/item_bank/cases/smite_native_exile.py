"""Native Exile identity, shield rune effects and ethereal repair qualification."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'smite-paladin-exile-off-hand-aura-recipe'
CONFIG = ROLE + '-stats'
RAW = (
    (194, 0, 4),
    (102, 0, 30),
    (134, 0, 1),
    (16, 0, 220),
    (151, 104, 13),
    (188, 25, 2),
    (198, 5253, 15),
    (252, 0, 25),
    (40, 0, 5),
    (44, 0, 5),
    (80, 0, 25),
    (74, 0, 7),
    (39, 0, 45),
    (41, 0, 45),
    (43, 0, 45),
    (45, 0, 45),
)
KEYS = (
    '102:0',
    '16:0',
    '151:104',
    '188:25',
    '198:5253',
    '252:0',
    '40:0',
    '44:0',
    '80:0',
    '74:0',
    '39:0',
    '41:0',
    '43:0',
    '45:0',
)


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        original = NativeRunewordItem(
            'Vortex Shield',
            quality,
            name='Exile',
            runeword='Exile',
            raw_stats=RAW,
            ethereal=True,
            sockets=4,
            socket_contents='filled',
            socket_items=tuple(SocketItem(name) for name in ('Vex Rune', 'Ohm Rune', 'Ist Rune', 'Dol Rune')),
        )
        ctx = {'player_class': 'Paladin'}
        no_repair = tuple(r for r in RAW if r[0] != 252)
        for label, item, context, truth in (
            ('native-minimum', original, ctx, 'true'),
            (
                'maximum-rolls',
                replace(
                    original,
                    raw_stats=tuple(
                        (s, layer, (275 if quality == 'superior' else 260) if s == 16 else 16 if s == 151 else value)
                        for s, layer, value in RAW
                    ),
                ),
                ctx,
                'true',
            ),
            ('sacred-targe', replace(original, base='Sacred Targe'), ctx, 'true'),
            ('heraldic-shield', replace(original, base='Heraldic Shield'), ctx, 'true'),
            ('nonethereal', replace(original, ethereal=False), ctx, 'true'),
            ('unread-repair', replace(original, raw_stats=no_repair), ctx, 'unknown'),
            ('known-no-repair', replace(original, raw_stats=no_repair, complete=True), ctx, 'false'),
            ('repair-not-needed', replace(original, ethereal=False, raw_stats=no_repair), ctx, 'true'),
            ('wrong-class', original, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            keys = tuple(k for k in KEYS if label != 'repair-not-needed' or k != '252:0')
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in keys})
                )
            yield Case(
                id=f'smite-native-exile/{quality}/{label}',
                item=item,
                context=context,
                covers=(ROLE,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (CONFIG,),
                # Vex/Ohm shield effects are not mana leech or enhanced weapon damage.
                absent_stat_configurations=dict.fromkeys(('62:0', '17:0', '18:0'), (CONFIG,)),
                report_contains=(
                    'Exile',
                    'Sockets: 4',
                    'Vex',
                    'Ohm',
                    'Ist',
                    'Dol',
                    '(220-275%)' if quality == 'superior' else '(220-260%)',
                    '(13-16)',
                )
                if label in ('native-minimum', 'maximum-rolls')
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/smite-paladin/slots/Off-Hand/0',
                    'third-parties/d2data/json/runes.json:/Exile',
                    'third-parties/d2data/json/gems.json:/r26',
                    'third-parties/d2data/json/gems.json:/r27',
                    'third-parties/d2data/json/gems.json:/r24',
                    'third-parties/d2data/json/gems.json:/r14',
                ),
            )


CASES = tuple(cases())
