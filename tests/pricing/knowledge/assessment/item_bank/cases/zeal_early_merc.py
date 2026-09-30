"""Early-game armor/helm alternatives serve both reviewed melee mercenaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'goldskin',
        215,
        Item(
            'Full Plate Mail',
            'unique',
            'Goldskin',
            ((16, 0, 120), (39, 0, 35), (41, 0, 35), (43, 0, 35), (45, 0, 35), (79, 0, 100)),
        ),
        ('39:0', '16:0', '79:0'),
    ),
    (
        'venom-ward',
        218,
        Item('Breast Plate', 'unique', 'Venom Ward', ((16, 0, 60), (45, 0, 90), (46, 0, 15), (110, 0, 50))),
        ('45:0', '46:0', '110:0'),
    ),
    (
        'rockfleece',
        216,
        Item('Field Plate', 'unique', 'Rockfleece', ((36, 0, 10), (34, 0, 5), (0, 0, 5))),
        ('36:0', '34:0', '0:0'),
    ),
    (
        'skin-of-the-flayed-one',
        214,
        Item('Demonhide Armor', 'unique', 'Skin of the Flayed One', ((60, 0, 5), (74, 0, 15))),
        ('60:0', '74:0'),
    ),
    (
        'the-face-of-horror',
        231,
        Item('Mask', 'unique', 'The Face of Horror', ((0, 0, 20), (39, 0, 10), (41, 0, 10), (43, 0, 10), (45, 0, 10))),
        ('0:0', '39:0', '45:0'),
    ),
    (
        'smoke',
        211,
        Item(
            'Breast Plate',
            'normal',
            'Smoke',
            ((39, 0, 50), (41, 0, 50), (43, 0, 50), (45, 0, 50), (99, 0, 20), (32, 0, 280)),
            runeword='Smoke',
            sockets=2,
            socket_contents='filled',
        ),
        ('39:0', '99:0', '32:0'),
    ),
    (
        'lionheart',
        212,
        Item(
            'Breast Plate',
            'normal',
            'Lionheart',
            (
                (17, 0, 20),
                (18, 0, 20),
                (7, 0, 50 * 256),
                (0, 0, 25),
                (2, 0, 15),
                (39, 0, 30),
                (41, 0, 30),
                (43, 0, 30),
                (45, 0, 30),
            ),
            runeword='Lionheart',
            sockets=3,
            socket_contents='filled',
        ),
        ('17:0', '7:0', '0:0'),
    ),
    (
        'temper',
        233,
        Item(
            'Bone Visage',
            'normal',
            'Temper',
            ((39, 0, 40), (142, 0, 10), (76, 0, 5), (99, 0, 20)),
            runeword='Temper',
            sockets=3,
            socket_contents='filled',
        ),
        ('39:0', '142:0', '99:0'),
    ),
    (
        'cure',
        234,
        Item(
            'Bone Visage',
            'normal',
            'Cure',
            ((151, 109, 1), (45, 0, 40), (110, 0, 50), (76, 0, 5), (99, 0, 20)),
            runeword='Cure',
            sockets=3,
            socket_contents='filled',
        ),
        ('151:109', '45:0', '99:0'),
    ),
)


def cases():
    result = []
    for slug, span, item, keys in EXAMPLES:
        for label, scenario, candidate, context in (
            ('might', 'positive', item, {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}),
            ('frenzy', 'positive', item, {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}),
            (
                'ethereal-frenzy',
                'positive',
                replace(item, ethereal=True),
                {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'},
            ),
            ('wrong-merc', 'negative', item, {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Bash'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {'player_class': 'Sorceress', 'mercenary_type': 'Act 5 Frenzy'}),
        ):
            role = (
                'zeal-paladin-smoke-act-5-frenzy'
                if slug == 'smoke' and context.get('mercenary_type') == 'Act 5 Frenzy'
                else f'zeal-paladin-{slug}-merc-survival-gear'
            )
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario],
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
                    id=f'zeal/early-merc/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(candidate.name,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
