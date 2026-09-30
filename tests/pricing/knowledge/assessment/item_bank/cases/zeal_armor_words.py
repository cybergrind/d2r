"""Player armor/helm alternatives constructed independently from native recipe values."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def RES(value):
    return tuple((stat, 0, value) for stat in (39, 41, 43, 45))


WORDS = (
    (
        'Enigma',
        'Mage Plate',
        3,
        113,
        (
            (127, 0, 2),
            (97, 54, 1),
            (96, 0, 45),
            (220, 0, 6),
            (240, 0, 8),
            (86, 0, 14),
            (31, 0, 1000),
            (76, 0, 5),
            (36, 0, 8),
            (114, 0, 15),
        ),
        ('127:0', '97:54', '96:0', '220:0', '240:0', '86:0', '31:0', '76:0', '36:0', '114:0'),
    ),
    (
        'Fortitude',
        'Archon Plate',
        4,
        114,
        (
            (17, 0, 300),
            (18, 0, 300),
            (16, 0, 200),
            (105, 0, 25),
            (201, 3855, 20),
            (114, 0, 12),
            (216, 0, 8 * 256),
            (34, 0, 7),
            (74, 0, 7),
            (42, 0, 5),
            *RES(25),
        ),
        (
            '17:0',
            '18:0',
            '16:0',
            '105:0',
            '201:3855',
            '114:0',
            '216:0',
            '34:0',
            '74:0',
            '42:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
        ),
    ),
    (
        'Chains of Honor',
        'Archon Plate',
        4,
        115,
        (
            (127, 0, 2),
            (16, 0, 70),
            (121, 0, 200),
            (122, 0, 100),
            (60, 0, 8),
            (0, 0, 20),
            (74, 0, 7),
            (36, 0, 8),
            (80, 0, 25),
            *RES(65),
        ),
        ('127:0', '16:0', '121:0', '122:0', '60:0', '0:0', '74:0', '36:0', '80:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Duress',
        'Mage Plate',
        3,
        120,
        (
            (17, 0, 10),
            (18, 0, 10),
            (16, 0, 150),
            (99, 0, 40),
            (135, 0, 33),
            (136, 0, 15),
            (54, 0, 37),
            (55, 0, 133),
            (56, 0, 50),
            (39, 0, 15),
            (41, 0, 15),
            (43, 0, 45),
            (45, 0, 15),
        ),
        ('17:0', '18:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Hustle (armor)',
        'Mage Plate',
        3,
        122,
        ((93, 0, 40), (96, 0, 65), (99, 0, 20), (97, 29, 6), (2, 0, 10), *RES(10)),
        ('93:0', '96:0', '99:0', '97:29', '2:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Lionheart',
        'Mage Plate',
        3,
        124,
        ((17, 0, 20), (18, 0, 20), (0, 0, 25), (2, 0, 15), (3, 0, 20), (7, 0, 50 * 256), (1, 0, 10), *RES(30)),
        ('17:0', '18:0', '0:0', '2:0', '3:0', '7:0', '1:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Smoke',
        'Mage Plate',
        2,
        125,
        ((16, 0, 75), (32, 0, 250), (99, 0, 20), (1, 0, 10), (204, 4614, 18 | 18 << 8), *RES(50)),
        ('16:0', '32:0', '99:0', '1:0', '204:4614', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'Bulwark',
        'Diadem',
        3,
        102,
        ((76, 0, 5), (16, 0, 75), (36, 0, 10), (74, 0, 30), (60, 0, 4), (99, 0, 20), (3, 0, 10), (34, 0, 7)),
        ('76:0', '16:0', '36:0', '74:0', '60:0', '99:0', '3:0', '34:0'),
    ),
    (
        'Temper',
        'Diadem',
        3,
        103,
        ((76, 0, 5), (16, 0, 75), (39, 0, 40), (142, 0, 10), (99, 0, 20), (3, 0, 10)),
        ('76:0', '16:0', '39:0', '142:0', '99:0', '3:0'),
    ),
)


def cases():
    result = []
    for name, base, sockets, span, raw, keys in WORDS:
        slug = name.split(' (')[0].lower().replace(' ', '-')
        role = 'zeal-paladin-' + slug + '-player-equipment-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            captured = tuple(
                (stat, layer, 870 if name == 'Enigma' and quality == 'low_quality' and stat == 31 else value)
                for stat, layer, value in raw
            )
            item = Item(base, quality, name, captured, sockets=sockets, socket_contents='filled', runeword=name)
            variants = [
                ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-family', replace(item, base='Crystal Sword'), {'player_class': 'Paladin'}, 'negative'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Paladin'}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('wrong-sockets', replace(item, sockets=1), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if name == 'Smoke':
                variants += [
                    (
                        'depleted-charges',
                        replace(
                            item,
                            raw_stats=tuple(
                                (stat, layer, 18 << 8 if stat == 204 else value) for stat, layer, value in raw
                            ),
                        ),
                        {'player_class': 'Paladin'},
                        'positive',
                    ),
                    (
                        'unknown-charges',
                        replace(item, raw_stats=tuple(row for row in raw if row[0] != 204)),
                        {'player_class': 'Paladin'},
                        'positive',
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
                if label == 'wrong-family':
                    expected = {'family': 'weapon'}
                no_charge = label in ('depleted-charges', 'unknown-charges')
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in keys
                                if not (no_charge and key == '204:4614')
                            }
                        )
                    )
                result.append(
                    Case(
                        id=f'zeal/armor-words/{slug}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        absent_stat_configurations={'204:4614': (role + '-stats',)} if no_charge else {},
                        report_contains=(name.split(' (')[0],),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
