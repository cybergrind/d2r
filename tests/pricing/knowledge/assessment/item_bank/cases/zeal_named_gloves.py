"""Standalone offensive gloves; no implied attack speed or set companions."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROWS = (
    (
        133,
        'zeal-paladin-steelrend-zeal-ranged-tail',
        Item('Ogre Gauntlets', 'unique', 'Steelrend', ((17, 0, 30), (18, 0, 30), (136, 0, 10), (0, 0, 15))),
        ('17:0', '18:0', '136:0', '0:0'),
    ),
    (
        136,
        'zeal-paladin-magnus-skin-zeal-ranged-tail',
        Item('Sharkskin Gloves', 'set', "Magnus' Skin", ((93, 0, 20), (19, 0, 100), (39, 0, 15), (16, 0, 50))),
        ('93:0', '19:0', '39:0', '16:0'),
    ),
)


def cases():
    result = []
    for span, role, item, keys in ROWS:
        for scenario, context in (
            ('positive', {'player_class': 'Paladin'}),
            ('negative', {'player_class': 'Sorceress'}),
            ('unknown', {}),
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
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/named-gloves/{item.name}/{scenario}',
                    item=item,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(item.name, 'Trade tier:'),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
