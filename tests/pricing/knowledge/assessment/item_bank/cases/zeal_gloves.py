"""Standalone glove benefits must bind to the intended build and wearer context."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'Laying of Hands',
        'Bramble Mitts',
        'set',
        'laying-of-hands',
        ((93, 0, 20), (121, 0, 350), (39, 0, 50)),
        ('93:0', '121:0'),
    ),
    (
        "Dracul's Grasp",
        'Vampirebone Gloves',
        'unique',
        'dracul-s-grasp',
        ((198, 5258, 5), (135, 0, 25), (0, 0, 10), (86, 0, 5), (60, 0, 7)),
        ('198:5258', '60:0'),
    ),
    ("Trang-Oul's Claws", 'Heavy Bracers', 'set', 'trang-oul-s-claws', ((105, 0, 20), (43, 0, 30)), ('105:0', '43:0')),
    (
        'Bloodfist',
        'Heavy Gloves',
        'unique',
        'bloodfist',
        ((7, 0, 40 << 8), (99, 0, 30), (93, 0, 10), (21, 0, 5)),
        ('99:0', '21:0'),
    ),
    (
        'Chance Guards',
        'Chain Gloves',
        'unique',
        'chance-guards',
        ((80, 0, 25), (79, 0, 200), (19, 0, 25)),
        ('80:0', '19:0'),
    ),
    (
        'Lava Gout',
        'Battle Gauntlets',
        'unique',
        'lava-gout',
        ((93, 0, 20), (39, 0, 24), (118, 0, 1), (198, 3338, 2)),
        ('93:0', '198:3338'),
    ),
)


def cases():
    result = []
    for name, base, quality, slug, stats, keys in SPECS:
        role = slug + '-zeal-gloves'
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
                    id='zeal/gloves/' + slug + '/' + scenario,
                    item=Item(base, quality, name, stats),
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        'pricing/raw/mr/guides__zeal-paladin.html:gear-table',
                        'third-parties/d2data/json/' + ('setitems' if quality == 'set' else 'uniqueitems') + '.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
