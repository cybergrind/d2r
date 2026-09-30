"""Memory Energy Shield prebuffs; item Telekinesis never supplies hard-point synergy."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


MAIN = ('blizzard-sorceress', 'enchant-sorceress', 'meteor-sorceress', 'nova-sorceress-guide')
GEAR = (
    ('frozen-orb-sorceress', 29),
    ('frozen-orb-meteor-sorceress', 29),
    ('fire-wall-sorceress-guide', 30),
    ('hydra-sorceress', 29),
)
ROLES = tuple(g + '-player-memory-weapon-swap-main-alternatives-word-utility-alternative' for g in MAIN) + tuple(
    g + '-memory-caster-recipe-gear' for g, _ in GEAR
)
RUNES = tuple(SocketItem(n + ' Rune') for n in ('Lum', 'Io', 'Sol', 'Eth'))


def memory(quality, staffmod=0):
    return NativeRunewordItem(
        'Battle Staff',
        quality,
        'Memory',
        (
            (194, 0, 4),
            (83, 1, 3),
            (107, 58, 3 + staffmod),
            (107, 42, 2),
            (105, 0, 33),
            (77, 0, 20),
            (35, 0, 7),
            (16, 0, 50),
            (1, 0, 10),
            (3, 0, 10),
            (21, 0, 9),
            (116, 0, -25),
        ),
        sockets=4,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Memory',
        complete=True,
    )


def cases():
    configs = tuple(r + '-stats' for r in ROLES)
    context = {'player_class': 'Sorceress'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = memory(quality)
        maximum_staffmod = 1 if quality == 'low_quality' else 3
        rows = [
            ('recipe-only', item, context, 'true'),
            ('native-max-es', memory(quality, maximum_staffmod), context, 'true'),
            (
                'item-telekinesis',
                replace(item, raw_stats=(*item.raw_stats, (107, 43, maximum_staffmod))),
                context,
                'true',
            ),
            ('ethereal', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal', observation(item, ethereal=None), context, 'true'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
            ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ]
        for label, candidate, loadout, truth in rows:
            bad_identity = label in ('wrong-recipe', 'empty', 'unidentified')
            assessment = (
                {}
                if bad_identity
                else {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in ROLES))}
            )
            if truth == 'true':
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('83:1', '107:58')}
                    )
                )
            expected = {'assessment': IsPartialDict(**assessment)}
            if bad_identity:
                expected['extraction'] = IsPartialDict(item=IsPartialDict(runeword=None))
            elif label in ('recipe-only', 'native-max-es'):
                expected['extraction'] = IsPartialDict(
                    item=IsPartialDict(runeword='Memory'),
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=107, layer=58),
                            value=3 + maximum_staffmod if label == 'native-max-es' else 3,
                        ),
                        IsPartialDict(memory_stat=IsPartialDict(id=83, layer=1), value=3),
                    ),
                )
            yield Case(
                id=f'memory-caster/{quality}/{label}',
                item=candidate,
                context=loadout,
                covers=ROLES,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected=expected,
                absent_configurations=() if truth == 'true' else configs,
                absent_stat_configurations=dict.fromkeys(('107:43', '107:42', '105:0', '21:0'), configs),
                report_contains=('Memory', 'Sockets: 4 — Lum, Io, Sol, Eth') if label == 'recipe-only' else (),
                evidence=(
                    'third-parties/d2data/json/runes.json:/Memory',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Weapon-Swap/1' for g in MAIN),
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{g}.html/sections/{s}'
                        for g, s in GEAR
                    ),
                ),
            )


CASES = tuple(cases())
