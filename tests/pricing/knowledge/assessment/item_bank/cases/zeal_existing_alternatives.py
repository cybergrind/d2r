"""Previously reviewed Zeal alternatives now exercised through published appraisal."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROWS = (
    (
        'Death Cleaver',
        'Berserker Axe',
        'zeal-death-cleaver-alternative',
        57,
        ((17, 0, 230), (18, 0, 230), (93, 0, 40), (141, 0, 66), (116, 0, 33), (86, 0, 6), (152, 0, 1)),
        ('17:0', '18:0', '93:0', '141:0', '116:0', '86:0'),
    ),
    (
        "Razor's Edge",
        'Tomahawk',
        'zeal-paladin-razor-s-edge-zeal-ranged-tail',
        65,
        ((17, 0, 175), (18, 0, 175), (93, 0, 40), (116, 0, 33), (141, 0, 50), (135, 0, 50)),
        ('17:0', '18:0', '93:0', '116:0', '141:0', '135:0'),
    ),
    (
        "Butcher's Pupil",
        'Small Crescent',
        'zeal-paladin-butcher-s-pupil-gear-alternatives-delivery-weapon',
        66,
        ((17, 0, 150), (18, 0, 150), (93, 0, 30), (141, 0, 35), (135, 0, 25), (152, 0, 1)),
        ('17:0', '18:0', '93:0', '141:0', '135:0'),
    ),
    (
        'Honor',
        'Naga',
        'zeal-paladin-honor-gear-alternatives-source-recipe',
        67,
        (
            (17, 0, 160),
            (18, 0, 160),
            (19, 0, 250),
            (141, 0, 25),
            (127, 0, 1),
            (60, 0, 7),
            (0, 0, 10),
            (74, 0, 10),
            (138, 0, 2),
        ),
        ('17:0', '18:0', '19:0', '141:0', '127:0', '60:0', '0:0', '74:0', '138:0'),
    ),
    (
        'Alma Negra',
        'Sacred Rondache',
        'zeal-paladin-alma-negra-zeal-ranged-tail',
        72,
        ((83, 3, 1), (102, 0, 30), (20, 0, 20), (35, 0, 5), (119, 0, 40), (17, 0, 40), (18, 0, 40), (16, 0, 180)),
        ('83:3', '102:0', '20:0', '35:0', '119:0', '17:0', '18:0', '16:0'),
    ),
    (
        'Leviathan',
        'Kraken Shell',
        'zeal-paladin-leviathan-zeal-ranged-tail',
        118,
        ((36, 0, 15), (0, 0, 40), (16, 0, 170), (31, 0, 1514), (152, 0, 1)),
        ('36:0', '0:0', '16:0', '31:0'),
    ),
    (
        'Stone',
        'Archon Plate',
        'zeal-paladin-stone-gear-alternatives-source-recipe',
        119,
        (
            (16, 0, 250),
            (32, 0, 300),
            (99, 0, 60),
            (0, 0, 16),
            (3, 0, 16),
            (1, 0, 10),
            (39, 0, 15),
            (41, 0, 15),
            (43, 0, 15),
            (45, 0, 15),
        ),
        ('16:0', '32:0', '99:0', '0:0', '3:0', '1:0', '39:0', '41:0', '43:0', '45:0'),
    ),
)


def cases():
    result = []
    for name, base, role, span, raw, keys in ROWS:
        word = name in ('Honor', 'Stone')
        for quality in ('normal', 'superior', 'low_quality') if word else ('unique',):
            item = Item(
                base,
                quality,
                name,
                raw,
                sockets=5 if name == 'Honor' else 4 if name == 'Stone' else 0,
                socket_contents='filled' if word else 'empty',
                runeword=name if word else None,
            )
            if name == 'Death Cleaver':
                item = replace(
                    item, ethereal=True, sockets=1, socket_contents='filled', socket_items=(SocketItem('Zod Rune'),)
                )
            for scenario, context in [
                ('positive', {'player_class': 'Paladin'}),
                ('negative', {'player_class': 'Sorceress'}),
                ('unknown', {}),
            ]:
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
                        id=f'zeal/existing-alternatives/{name}/{quality}/{scenario}',
                        item=item,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        report_contains=(name,) if word else (name, 'Trade tier:'),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
