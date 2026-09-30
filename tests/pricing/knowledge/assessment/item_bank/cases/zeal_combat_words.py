"""Explicit Zeal weapon bases, low rolls, durability and missing context."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


WORDS = (
    (
        'grief',
        'Grief',
        'Phase Blade',
        False,
        5,
        54,
        ((111, 0, 340), (93, 0, 30), (141, 0, 20), (115, 0, 1), (116, 0, 25), (243, 0, 15), (86, 0, 10)),
        ('111:0', '93:0', '141:0', '115:0', '116:0', '243:0', '86:0'),
    ),
    (
        'oath',
        'Oath',
        'Cryptic Sword',
        True,
        4,
        62,
        ((17, 0, 210), (18, 0, 210), (93, 0, 50), (152, 0, 1), (147, 0, 10), (121, 0, 75), (123, 0, 100)),
        ('17:0', '93:0', '147:0', '121:0', '123:0'),
    ),
    (
        'last-wish',
        'Last Wish',
        'Phase Blade',
        False,
        6,
        55,
        ((17, 0, 330), (18, 0, 330), (136, 0, 60), (151, 98, 17), (198, 5266, 10), (201, 17099, 6), (115, 0, 1)),
        ('17:0', '136:0', '151:98', '198:5266', '201:17099', '115:0'),
    ),
)


def cases():
    result = []
    for slug, name, base, ethereal, sockets, span, raw, keys in WORDS:
        role = 'zeal-paladin-' + slug + '-weapon-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base, quality, name, raw, ethereal=ethereal, sockets=sockets, socket_contents='filled', runeword=name
            )
            variants = [
                ('low-roll', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-base', replace(item, base='Berserker Axe'), {'player_class': 'Paladin'}, 'negative'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-player', item, {}, 'unknown'),
            ]
            if name == 'Oath':
                variants.extend(
                    (
                        ('nonethereal-variant', replace(item, ethereal=False), {'player_class': 'Paladin'}, 'negative'),
                        (
                            'invalid-indestructible-flag',
                            replace(
                                item,
                                raw_stats=tuple(
                                    (stat, layer, 0 if stat == 152 else value) for stat, layer, value in raw
                                ),
                            ),
                            {'player_class': 'Paladin'},
                            'unknown',
                        ),
                        (
                            'complete-no-indestructible',
                            replace(item, raw_stats=tuple(r for r in raw if r[0] != 152), complete=True),
                            {'player_class': 'Paladin'},
                            'negative',
                        ),
                    )
                )
                variants.append(
                    (
                        'missing-indestructible',
                        replace(item, raw_stats=tuple(r for r in raw if r[0] != 152)),
                        {'player_class': 'Paladin'},
                        'unknown',
                    )
                )
            for label, candidate, context, scenario in variants:
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
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
                result.append(
                    Case(
                        id=f'zeal/combat-words/{slug}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        report_contains=(name,),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
