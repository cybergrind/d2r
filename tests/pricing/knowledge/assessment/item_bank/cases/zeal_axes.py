"""Zeal axe variants preserve durability, physical attacks and aura recipients."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


WORDS = (
    (
        'death',
        'Death',
        True,
        5,
        56,
        (
            (17, 0, 300),
            (18, 0, 300),
            (136, 0, 50),
            (250, 0, 4),
            (119, 0, 20),
            (19, 0, 50),
            (62, 0, 7),
            (152, 0, 1),
            (195, 3538, 25),
        ),
        ('17:0', '136:0', '250:0', '119:0', '19:0', '62:0', '195:3538'),
    ),
    (
        'breath-of-the-dying',
        'Breath of the Dying',
        True,
        6,
        58,
        (
            (17, 0, 350),
            (18, 0, 350),
            (93, 0, 60),
            (60, 0, 12),
            (62, 0, 7),
            (0, 0, 30),
            (2, 0, 30),
            (3, 0, 30),
            (1, 0, 30),
            (19, 0, 50),
            (116, 0, 25),
            (152, 0, 1),
            (122, 0, 200),
            (124, 0, 50),
            (117, 0, 1),
        ),
        ('17:0', '93:0', '60:0', '62:0', '0:0', '2:0', '3:0', '19:0', '116:0', '122:0', '124:0', '117:0'),
    ),
    (
        'doom',
        'Doom',
        False,
        5,
        61,
        (
            (17, 0, 330),
            (18, 0, 330),
            (93, 0, 45),
            (151, 114, 12),
            (305, 0, 40),
            (127, 0, 2),
            (141, 0, 20),
            (135, 0, 25),
            (117, 0, 1),
        ),
        ('17:0', '93:0', '151:114', '305:0', '127:0', '141:0', '135:0', '117:0'),
    ),
)


def cases():
    result = []
    for slug, name, eth, sockets, span, raw, keys in WORDS:
        role = 'zeal-paladin-' + slug + '-weapon-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Berserker Axe',
                quality,
                name,
                raw,
                ethereal=eth,
                sockets=sockets,
                socket_contents='filled',
                runeword=name,
            )
            variants = [
                ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-base', replace(item, base='Champion Axe'), {'player_class': 'Paladin'}, 'negative'),
                ('wrong-ethereal', replace(item, ethereal=not eth), {'player_class': 'Paladin'}, 'negative'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-player', item, {}, 'unknown'),
            ]
            if eth:
                variants += [
                    (
                        'unknown-indestructible',
                        replace(item, raw_stats=tuple(r for r in raw if r[0] != 152)),
                        {'player_class': 'Paladin'},
                        'unknown',
                    ),
                    (
                        'absent-indestructible',
                        replace(item, raw_stats=tuple(r for r in raw if r[0] != 152), complete=True),
                        {'player_class': 'Paladin'},
                        'negative',
                    ),
                ]
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
                        id=f'zeal/axes/{slug}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        absent_stat_configurations={'1:0': (role + '-stats',)} if name == 'Breath of the Dying' else {},
                        report_contains=(name,),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
