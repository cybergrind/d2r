"""A valuable +Poison Nova trophy is distinct from a generic Rhyme shield."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'poison-nova-necromancer-0-rhyme'
# Fetish Trophy base block 5 + recipe 20; Shael adds 20 to recipe's 20 FBR.
STATS = (
    (107, 92, 2),
    (31, 0, 50),
    (20, 0, 25),
    (102, 0, 40),
    (39, 0, 25),
    (41, 0, 25),
    (43, 0, 25),
    (45, 0, 25),
    (153, 0, 1),
    (80, 0, 25),
    (79, 0, 50),
    (27, 0, 15),
    (194, 0, 2),
)


def cases():
    context = {'player_class': 'Necromancer'}
    config = ROLE + '-stats'
    for quality in ('normal', 'superior'):
        original = NativeRunewordItem(
            'Fetish Trophy',
            quality,
            'Rhyme',
            STATS,
            sockets=2,
            socket_contents='filled',
            runeword='Rhyme',
            socket_items=(SocketItem('Shael Rune'), SocketItem('Eth Rune')),
        )
        variants = [
            ('source-staffmod', original, context, 'true'),
            ('wrong-class', original, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('ethereal-player-shield', replace(original, ethereal=True), context, 'false'),
            ('different-head', replace(original, base='Mummified Trophy'), context, 'false'),
        ]
        for label, bonus, truth in [('perfect-staffmod', 3, 'true'), ('one-point', 1, 'false')]:
            variants.append(
                (
                    label,
                    replace(
                        original, raw_stats=tuple((s, p, bonus if (s, p) == (107, 92) else v) for s, p, v in STATS)
                    ),
                    context,
                    truth,
                )
            )
        without_skill = tuple(row for row in STATS if row[:2] != (107, 92))
        variants.extend(
            (
                ('unread-staffmod', replace(original, raw_stats=without_skill), context, 'unknown'),
                ('absent-staffmod', replace(original, raw_stats=without_skill, complete=True), context, 'false'),
            )
        )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('107:92', '153:0', '80:0', '102:0', '20:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'poison-rhyme-staffmods/{quality}/{label}',
                item=item,
                context=ctx,
                covers=(ROLE,),
                scenario='positive' if active else 'negative' if truth == 'false' else 'unknown',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                report_contains=(
                    'Rhyme',
                    'Sockets: 2 — Shael, Eth',
                    'Poison Nova',
                    'staffmod range: 1-3',
                    '40% Faster Block Rate',
                    'Cannot Be Frozen',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/0',
                    'third-parties/d2data/json/runes.json:/Rhyme',
                    'third-parties/d2data/json/armor.json:/ne7',
                ),
            )


CASES = tuple(cases())
