"""Native Blood glove and rare resistance-belt examples, including unread cores."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROWS = (
    (
        'blood-gloves',
        127,
        Item(
            'Vampirebone Gloves',
            'crafted',
            raw_stats=((93, 0, 20), (60, 0, 1), (136, 0, 5), (7, 0, 10 * 256), (0, 0, 10), (41, 0, 21), (80, 0, 16)),
        ),
        93,
        ('93:0', '60:0', '136:0', '7:0', '0:0', '41:0', '80:0'),
    ),
    (
        'rare-belt',
        144,
        Item(
            'Vampirefang Belt',
            'rare',
            raw_stats=((99, 0, 24), (0, 0, 21), (7, 0, 41 * 256), (39, 0, 21), (41, 0, 21), (43, 0, 21)),
        ),
        99,
        ('99:0', '0:0', '7:0', '39:0', '41:0', '43:0'),
    ),
)


def cases():
    result = []
    for slug, span, item, missing, keys in ROWS:
        role = 'zeal-paladin-' + slug + '-alternative'
        for scenario, label, candidate, context in (
            ('positive', 'low-native-rolls', item, {'player_class': 'Paladin'}),
            ('negative', 'wrong-class', item, {'player_class': 'Sorceress'}),
            ('unknown', 'unknown-class', item, {}),
            (
                'negative',
                'missing-core',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != missing), complete=True),
                {'player_class': 'Paladin'},
            ),
            (
                'unknown',
                'unread-core',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != missing)),
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
                    id=f'zeal/affixed-accessories/{slug}/{label}',
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
