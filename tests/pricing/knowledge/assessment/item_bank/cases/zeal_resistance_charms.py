"""Each elemental resistance is an alternative, not a four-element sum."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    result = []
    for slug, base, threshold, span in (
        ('small-resistance', 'Small Charm', 10, 183),
        ('grand-resistance', 'Grand Charm', 26, 194),
    ):
        role = f'zeal-paladin-charm-{slug}'
        scenarios = []
        for key, element in ((39, 'fire'), (41, 'lightning'), (43, 'cold'), (45, 'poison')):
            item = Item(base, 'magic', raw_stats=((key, 0, threshold),), complete=True)
            scenarios.extend(
                (
                    ('positive', element, item, {'player_class': 'Paladin'}, key),
                    (
                        'negative',
                        element + '-below',
                        replace(item, raw_stats=((key, 0, threshold - 1),)),
                        {'player_class': 'Paladin'},
                        None,
                    ),
                )
            )
        item = Item(base, 'magic', raw_stats=((39, 0, threshold),), complete=True)
        scenarios.extend(
            (
                ('negative', 'wrong-class', item, {'player_class': 'Sorceress'}, None),
                ('unknown', 'unknown-class', item, {}, None),
                ('negative', 'missing', replace(item, raw_stats=()), {'player_class': 'Paladin'}, None),
                ('unknown', 'unread', replace(item, raw_stats=(), complete=False), {'player_class': 'Paladin'}, None),
                (
                    'negative',
                    'sum-not-enough',
                    replace(item, raw_stats=tuple((key, 0, threshold - 1) for key in (39, 41, 43, 45))),
                    {'player_class': 'Paladin'},
                    None,
                ),
                ('negative', 'wrong-size', replace(item, base='Large Charm'), {'player_class': 'Paladin'}, None),
            )
        )
        for scenario, label, item, context, stat in scenarios:
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
            if label == 'wrong-size':
                expected = {'family': 'charm'}
            if stat:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({f'{stat}:0': IsPartialDict(configuration_ids=Contains(role + '-stats'))})
                )
            result.append(
                Case(
                    id=f'zeal/resistance-charms/{slug}/{label}',
                    item=item,
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
