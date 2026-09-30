"""Abyss player words: minimum rolls, rune contributions and separate swap use."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def res(value):
    return tuple((s, 0, value) for s in (39, 41, 43, 45))


SPIRIT = ((127, 0, 2), (105, 0, 25), (99, 0, 55), (9, 0, 89 * 256), (3, 0, 22), (32, 0, 250), (147, 0, 3))
EXAMPLES = (
    (
        'hoto',
        9,
        'Heart of the Oak',
        'Flail',
        4,
        'Weapon',
        ((127, 0, 3), (105, 0, 40), (77, 0, 15), (74, 0, 20), (2, 0, 10), *res(30)),
        ('127:0', '105:0', '77:0', '39:0', '74:0'),
        (),
    ),
    (
        'spirit-sword',
        10,
        'Spirit',
        'Crystal Sword',
        4,
        'Weapon',
        (*SPIRIT, (60, 0, 7)),
        ('127:0', '105:0', '99:0', '9:0', '3:0'),
        ('60:0',),
    ),
    (
        'plague',
        11,
        'Plague',
        'Kriss',
        3,
        'Weapon',
        ((127, 0, 1), (151, 109, 13), (17, 0, 220), (18, 0, 220), (93, 0, 20), (336, 0, 23), (201, 91 * 64 + 20, 12)),
        ('127:0', '151:109'),
        ('17:0', '18:0', '93:0', '336:0', '201:5844'),
    ),
    (
        'obsession',
        12,
        'Obsession',
        'War Staff',
        6,
        'Weapon',
        (
            (127, 0, 4),
            (105, 0, 65),
            (99, 0, 60),
            (76, 0, 15),
            (27, 0, 15),
            (80, 0, 30),
            (79, 0, 75),
            (1, 0, 10),
            (3, 0, 10),
            *res(60),
        ),
        ('127:0', '105:0', '99:0', '76:0', '27:0', '80:0'),
        (),
    ),
    (
        'spirit-shield',
        23,
        'Spirit',
        'Monarch',
        4,
        'Off-Hand',
        (*SPIRIT, (41, 0, 35), (43, 0, 35), (45, 0, 35)),
        ('127:0', '105:0', '99:0', '9:0', '41:0'),
        (),
    ),
    (
        'splendor',
        25,
        'Splendor',
        'Small Shield',
        2,
        'Off-Hand',
        ((127, 0, 1), (105, 0, 10), (102, 0, 20), (16, 0, 60), (80, 0, 20), (79, 0, 50), (27, 0, 15), (1, 0, 10)),
        ('127:0', '105:0', '102:0', '80:0', '27:0'),
        (),
    ),
    (
        'pledge',
        27,
        "Ancients' Pledge",
        'Kite Shield',
        3,
        'Off-Hand',
        ((39, 0, 48), (41, 0, 48), (43, 0, 43), (45, 0, 48), (16, 0, 50)),
        ('39:0', '41:0', '43:0', '45:0'),
        (),
    ),
    (
        'rhyme',
        28,
        'Rhyme',
        'Small Shield',
        2,
        'Off-Hand',
        ((153, 0, 1), (80, 0, 25), (79, 0, 50), (102, 0, 40), (20, 0, 20), (27, 0, 15), *res(25)),
        ('153:0', '80:0', '102:0', '20:0', '39:0', '27:0'),
        (),
    ),
    (
        'spirit-swap',
        34,
        'Spirit',
        'Monarch',
        4,
        'Off-Hand-Swap',
        (*SPIRIT, (41, 0, 35), (43, 0, 35), (45, 0, 35)),
        ('127:0',),
        ('105:0', '99:0', '9:0', '41:0'),
    ),
)


def cases():
    context = {'player_class': 'Warlock'}
    for slug, span, name, base, sockets, slot, raw, keys, irrelevant in EXAMPLES:
        role = 'abyss-warlock-player-word-' + slug
        item = Item(base, 'normal', name, raw, sockets=sockets, socket_contents='filled', runeword=name)
        rows = [('native-low', item, context, 'positive')]
        rows += [
            (quality, replace(item, rarity=quality), context, 'positive') for quality in ('superior', 'low_quality')
        ]
        rows += [
            ('wrong-class', item, {'player_class': 'Paladin'}, 'negative'),
            ('unknown-class', item, {}, 'unknown'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('empty', replace(item, socket_contents='empty'), context, 'negative'),
            (
                'wrong-base',
                replace(
                    item,
                    base={
                        'hoto': 'Knout',
                        'spirit-sword': 'Broad Sword',
                        'plague': 'Dagger',
                        'obsession': 'Short Staff',
                    }.get(slug, 'Buckler'),
                ),
                context,
                'negative',
            ),
            ('ethereal', replace(item, ethereal=True), context, 'negative' if slot == 'Off-Hand' else 'positive'),
            (
                'unknown-ethereal',
                replace(item, ethereal=None),
                context,
                'unknown' if slot == 'Off-Hand' else 'positive',
            ),
        ]
        for label, candidate, ctx, scenario in rows:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='player',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'abyss/player-words/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                report_contains=(name,),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                ),
            )


CASES = tuple(cases())
