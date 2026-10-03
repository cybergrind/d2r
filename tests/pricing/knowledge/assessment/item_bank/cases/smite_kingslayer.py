"""Smite values Kingslayer's fixed attack utility, not its variable weapon ED."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'smite-paladin-kingslayer-main-alternatives-source-recipe'
CONFIG = ROLE + '-stats'
RUNES = tuple(SocketItem(name + ' Rune') for name in ('Mal', 'Um', 'Gul', 'Fal'))


def kingslayer(quality, damage=230):
    # Um contributes another 25 Open Wounds; Gul supplies AR and Fal Strength.
    return NativeRunewordItem(
        'Phase Blade',
        quality,
        'Kingslayer',
        (
            (17, 0, damage),
            (18, 0, damage),
            (93, 0, 30),
            (116, 0, 25),
            (136, 0, 33),
            (135, 0, 50),
            (97, 111, 1),
            (79, 0, 40),
            (117, 0, 1),
            (119, 0, 20),
            (0, 0, 10),
            (194, 0, 4),
        ),
        sockets=4,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Kingslayer',
    )


def cases():
    context = {'player_class': 'Paladin'}
    priorities = {'93:0': 'desirable', '136:0': 'desirable', '135:0': 'desirable', '0:0': 'supporting'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = kingslayer(quality)
        examples = [
            ('minimum-ed', item, context, 'true'),
            ('maximum-ed', kingslayer(quality, 270), context, 'true'),
            ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        if quality == 'normal':
            examples.extend(
                (
                    ('wrong-base', replace(item, base='Crystal Sword'), context, 'false'),
                    ('missing-rune', replace(item, socket_items=RUNES[:-1]), context, None),
                    ('reversed-runes', replace(item, socket_items=RUNES[::-1]), context, None),
                    ('unidentified', replace(item, identified=False), context, None),
                    ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                    (
                        'unknown-sockets',
                        observation(
                            item,
                            sockets=None,
                            socket_items=(),
                            socket_contents='unknown',
                            raw_stats=tuple(r for r in item.raw_stats if r[0] != 194),
                        ),
                        context,
                        'unknown',
                    ),
                    (
                        'uncaptured-ias',
                        replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 93)),
                        context,
                        'true',
                    ),
                )
            )
        for label, candidate, loadout, truth in examples:
            supported = truth == 'true'
            captured = {f'{s}:{p}' for s, p, _ in candidate.raw_stats}
            assessment = {}
            if truth is not None:
                assessment['roles'] = Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))
            if supported:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(IsPartialDict(configuration_id=CONFIG, desirability=grade))
                            )
                            for key, grade in priorities.items()
                            if key in captured
                        }
                    )
                )
            absent = dict.fromkeys(('17:0', '18:0', '119:0', '116:0', '97:111', '79:0'), (CONFIG,))
            absent.update({key: (CONFIG,) for key in priorities if key not in captured})
            yield Case(
                id=f'smite-kingslayer/{quality}/{label}',
                item=candidate,
                context=loadout,
                covers=(ROLE,),
                scenario='positive' if supported else 'unknown' if 'unknown' in label else 'negative',
                expected={'assessment': IsPartialDict(**assessment)},
                absent_configurations=() if supported else (CONFIG,),
                absent_stat_configurations=absent,
                report_contains=('Kingslayer', 'Sockets: 4 — Mal, Um, Gul, Fal') if label == 'minimum-ed' else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/smite-paladin/slots/Weapon/3',
                    'third-parties/d2data/json/runes.json:/Kingslayer',
                    'third-parties/d2data/json/gems.json:/r22',
                    'third-parties/d2data/json/weapons.json:/7cr',
                ),
            )


CASES = tuple(cases())
