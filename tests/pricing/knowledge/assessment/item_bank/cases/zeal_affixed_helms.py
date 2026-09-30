"""Zeal circlet casting utility and Blood helm physical utility are distinct."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CIRCLET = Item(
    'Diadem', 'rare', raw_stats=((83, 3, 2), (105, 0, 20), (225, 0, 2), (7, 0, 40 * 256), (80, 0, 25)), sockets=2
)
BLOOD = Item(
    'Armet', 'crafted', raw_stats=((60, 0, 3), (141, 0, 10), (7, 0, 60 * 256), (225, 0, 2), (16, 0, 200)), sockets=2
)


def cases():
    result = []
    for slug, item, span, keys, missing in (
        ('rare-circlet', CIRCLET, 98, ('83:3', '105:0', '225:0', '7:0', '80:0'), 105),
        ('blood-helm', BLOOD, 99, ('60:0', '141:0', '225:0', '7:0', '16:0'), 225),
    ):
        role = 'zeal-paladin-' + slug + '-alternative'
        for scenario, label, candidate, context in (
            ('positive', 'example', item, {'player_class': 'Paladin'}),
            ('negative', 'wrong-class', item, {'player_class': 'Sorceress'}),
            ('unknown', 'unknown-class', item, {}),
            (
                'negative',
                'missing-core-mod',
                replace(item, raw_stats=tuple(x for x in item.raw_stats if x[0] != missing), complete=True),
                {'player_class': 'Paladin'},
            ),
            (
                'unknown',
                'unread-core-mod',
                replace(item, raw_stats=tuple(x for x in item.raw_stats if x[0] != missing)),
                {'player_class': 'Paladin'},
            ),
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
                    id=f'zeal/affixed-helms/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(item.base,),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
