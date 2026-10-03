"""Enchant's Fire Rogue: native NL rolls and physical leech, not elemental sustain."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


ROLE = 'enchant-sorceress-0-merc-bulwark-native'
CONFIG = ROLE + '-stats'
RUNES = tuple(SocketItem(name + ' Rune') for name in ('Shael', 'Io', 'Sol'))
CAVEAT = (
    'The Fire Rogue receives Enchant and uses Insight; elemental damage and the player cast-rate breakpoint '
    'are not physical leech or a mercenary attack-speed target.'
)


def helmet(quality, maximum=False):
    defense = (115 if quality == 'superior' else 100) if maximum else 75
    return NativeRunewordItem(
        'Diadem',
        quality,
        'Bulwark',
        (
            (60, 0, 6 if maximum else 4),
            (36, 0, 15 if maximum else 10),
            (16, 0, defense),
            (76, 0, 5),
            (99, 0, 20),
            (74, 0, 30),
            (34, 0, 7),
            (3, 0, 10),
            (194, 0, 3),
        ),
        ethereal=True,
        sockets=3,
        socket_contents='filled',
        runeword='Bulwark',
        socket_items=RUNES,
    )


def cases():
    context = {'player_class': 'Sorceress', 'mercenary_type': 'Act 1 Fire'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = helmet(quality)
        examples = (
            ('minimum', item, context, 'true'),
            ('maximum', helmet(quality, True), context, 'true'),
            ('nonethereal', replace(item, ethereal=False), context, 'false'),
            ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
            ('different-base', replace(item, base='Crown'), context, 'false'),
            ('different-circlet', replace(item, base='Tiara'), context, 'false'),
            ('wrong-class', item, {**context, 'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {'mercenary_type': 'Act 1 Fire'}, 'unknown'),
            ('cold-rogue', item, {**context, 'mercenary_type': 'Act 1 Cold'}, 'false'),
            ('act-two', item, {**context, 'mercenary_type': 'Act 2 Might'}, 'false'),
            ('unknown-merc', item, {'player_class': 'Sorceress'}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
        )
        for label, candidate, loadout, truth in examples:
            active = truth == 'true'
            expected = {}
            if label not in ('unidentified', 'empty', 'wrong-recipe', 'different-base'):
                expected['roles'] = Contains(
                    IsPartialDict(
                        id=ROLE,
                        side='merc',
                        slot='Helmet',
                        rule_trace=IsPartialDict(truth=truth),
                        missing=Contains(CAVEAT),
                    )
                )
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(
                                        configuration_id=CONFIG,
                                        desirability=grade,
                                    )
                                )
                            )
                            for key, grade in (
                                ('60:0', 'desirable'),
                                ('36:0', 'desirable'),
                                ('76:0', 'supporting'),
                                ('99:0', 'supporting'),
                            )
                        }
                    )
                )
            yield Case(
                id=f'enchant-bulwark/{quality}/{label}',
                item=candidate,
                context=loadout,
                covers=(ROLE,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (CONFIG,),
                absent_roles=(ROLE,) if label == 'different-base' else (),
                absent_stat_configurations=dict.fromkeys(('3:0', '93:0', '105:0'), (CONFIG,)),
                report_contains=(
                    'Bulwark',
                    'Shael, Io, Sol',
                    '(4-6%) Life stolen per hit',
                    '(75-115%) Enhanced Defense' if quality == 'superior' else '(75-100%) Enhanced Defense',
                    f'Physical Damage Received Reduced by {15 if label == "maximum" else 10}% (10-15%)',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/enchant-sorceress/variants/0',
                    'third-parties/d2data/json/runes.json:/Bulwark',
                    'third-parties/d2data/json/gems.json',
                ),
            )


CASES = tuple(cases())
