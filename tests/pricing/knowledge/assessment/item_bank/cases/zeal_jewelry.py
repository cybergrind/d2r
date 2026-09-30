"""Jewelry native benefits must bind to the intended build and wearer context."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        "Highlord's Wrath",
        'Amulet',
        'highlord-s-wrath',
        ((127, 0, 1), (93, 0, 20), (41, 0, 35), (250, 0, 3)),
        ('93:0', '250:0'),
    ),
    (
        "Mara's Kaleidoscope",
        'Amulet',
        'mara-s-kaleidoscope',
        ((127, 0, 2), (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20)),
        ('127:0', '39:0'),
    ),
    (
        'Metalgrid',
        'Amulet',
        'metalgrid',
        ((31, 0, 300), (19, 0, 400), (39, 0, 25), (41, 0, 25), (43, 0, 25), (45, 0, 25)),
        ('31:0', '19:0'),
    ),
    (
        'Raven Frost',
        'Ring',
        'raven-frost',
        ((153, 0, 1), (148, 0, 20), (9, 0, 40 << 8), (2, 0, 15), (19, 0, 150)),
        ('153:0', '19:0'),
    ),
    ('Nagelring', 'Ring', 'nagelring', ((80, 0, 15), (19, 0, 50), (35, 0, 3)), ('80:0', '19:0')),
    ('Dwarf Star', 'Ring', 'dwarf-star', ((142, 0, 15), (35, 0, 12), (7, 0, 40 << 8), (79, 0, 100)), ('142:0', '7:0')),
    ('Wisp Projector', 'Ring', 'wisp-projector', ((144, 0, 10), (80, 0, 10)), ('144:0', '80:0')),
)


def cases():
    result = []
    for name, base, slug, stats, keys in SPECS:
        role = slug + '-zeal-jewelry'
        for scenario, context, status in (
            ('positive', {'player_class': 'Paladin'}, 'partial'),
            ('negative', {'player_class': 'Necromancer'}, 'failed'),
            ('unknown', {}, 'partial'),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        build='zeal-paladin',
                        status=status,
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
                    id='zeal/jewelry/' + slug + '/' + scenario,
                    item=Item(base, 'unique', name, stats),
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        'pricing/raw/mr/guides__zeal-paladin.html:gear-table',
                        'third-parties/d2data/json/uniqueitems.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
