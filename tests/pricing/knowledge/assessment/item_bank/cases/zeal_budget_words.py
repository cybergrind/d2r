"""Zeal budget words: no Barbarian skill or duplicate Fanaticism priority."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


WORDS = (
    (
        'unbending-will',
        'Unbending Will',
        6,
        63,
        (
            (17, 0, 300),
            (18, 0, 300),
            (93, 0, 20),
            (188, 32, 3),
            (198, 8786, 18),
            (60, 0, 8),
            (0, 0, 10),
            (3, 0, 10),
            (34, 0, 8),
            (117, 0, 1),
            (19, 0, 50),
            (122, 0, 75),
            (124, 0, 50),
            (22, 0, 149),  # 35 base * 4 from 300% ED, then Ith +9 maximum damage.,
        ),
        ('17:0', '93:0', '60:0', '0:0', '3:0', '34:0', '117:0', '19:0', '122:0', '124:0', '22:0', '198:8786'),
        '188:32',
    ),
    (
        'hustle',
        'Hustle (weapon)',
        3,
        64,
        (
            (17, 0, 180),
            (18, 0, 180),
            (93, 0, 30),
            (198, 16513, 5),
            (151, 122, 1),
            (2, 0, 10),
            (122, 0, 75),
            (124, 0, 50),
        ),
        ('17:0', '93:0', '198:16513', '2:0', '122:0', '124:0'),
        '151:122',
    ),
)


def cases():
    result = []
    for slug, name, sockets, span, raw, keys, excluded in WORDS:
        role = 'zeal-paladin-' + slug + '-weapon-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item('Phase Blade', quality, name, raw, sockets=sockets, socket_contents='filled', runeword=name)
            for label, candidate, context, scenario in (
                ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-base', replace(item, base='Cryptic Sword'), {'player_class': 'Paladin'}, 'negative'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'negative'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-player', item, {}, 'unknown'),
            ):
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
                        id=f'zeal/budget-words/{slug}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        absent_stat_configurations={excluded: (role + '-stats',)},
                        report_contains=(name.split(' (')[0],),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
            if slug == 'hustle':
                result.append(
                    Case(
                        id=f'zeal/budget-words/hustle/{quality}/armor-variant',
                        item=Item(
                            'Mage Plate',
                            quality,
                            'Hustle (armor)',
                            ((93, 0, 40), (96, 0, 65)),
                            sockets=3,
                            socket_contents='filled',
                            runeword='Hustle (armor)',
                        ),
                        context={'player_class': 'Paladin'},
                        expected={'assessment': IsPartialDict(family='armor')},
                        covers=(role,),
                        scenario='negative',
                        absent_configurations=(role + '-stats',),
                        evidence=('third-parties/d2data/json/runes.json:/Hustle (armor)',),
                    )
                )
    return tuple(result)


CASES = cases()
