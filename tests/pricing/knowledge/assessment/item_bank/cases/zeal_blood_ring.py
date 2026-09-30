"""Blood ring recipe and affix contributions use the exact linked planner."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'zeal-paladin-blood-ring-alternative'
ITEM = Item('Ring', 'crafted', raw_stats=((60, 0, 8), (7, 0, 41 * 256), (0, 0, 1), (21, 0, 6), (19, 0, 101)))


def cases():
    result = []
    for scenario, label, item, context in (
        ('positive', 'low-rolls', ITEM, {'player_class': 'Paladin'}),
        ('negative', 'wrong-class', ITEM, {'player_class': 'Sorceress'}),
        ('unknown', 'unknown-class', ITEM, {}),
        (
            'negative',
            'missing-leech',
            replace(ITEM, raw_stats=ITEM.raw_stats[1:], complete=True),
            {'player_class': 'Paladin'},
        ),
        ('unknown', 'unread-leech', replace(ITEM, raw_stats=ITEM.raw_stats[1:]), {'player_class': 'Paladin'}),
        (
            'negative',
            'recipe-only-leech',
            replace(ITEM, raw_stats=((60, 0, 3), *ITEM.raw_stats[1:])),
            {'player_class': 'Paladin'},
        ),
    ):
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    rule_trace=IsPartialDict(
                        truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                    ),
                )
            )
        }
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('60:0', '7:0', '0:0', '21:0', '19:0')
                    }
                )
            )
        result.append(
            Case(
                id=f'zeal/blood-ring/{label}',
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                report_contains=('Ring',),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/168',
                    'pricing/raw/mr/planners/1w0106kl.json:/data',
                ),
            )
        )
    return tuple(result)


CASES = cases()
