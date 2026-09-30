"""Equal damage totals must not erase the captured Maiming suffix distinction."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'zeal-paladin-charm-grand-sharp-maiming'
ITEM = Item(
    'Grand Charm', 'magic', raw_stats=((19, 0, 49), (22, 0, 10)), affix_records=(('prefix', 253), ('suffix', 678))
)


def cases():
    result = []
    for scenario, label, item, context in (
        ('positive', 'native-low-roll', ITEM, {'player_class': 'Paladin'}),
        (
            'negative',
            'plain-sharp-same-total',
            replace(ITEM, affix_records=(('prefix', 253),)),
            {'player_class': 'Paladin'},
        ),
        ('unknown', 'unread-affixes-same-total', replace(ITEM, affix_records=None), {'player_class': 'Paladin'}),
        (
            'negative',
            'below-combined-minimum',
            replace(ITEM, raw_stats=((19, 0, 49), (22, 0, 9))),
            {'player_class': 'Paladin'},
        ),
        ('unknown', 'unread-damage', replace(ITEM, raw_stats=((19, 0, 49),)), {'player_class': 'Paladin'}),
        ('negative', 'wrong-class', ITEM, {'player_class': 'Sorceress'}),
        ('unknown', 'unknown-class', ITEM, {}),
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
                    {k: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for k in ('19:0', '22:0')}
                )
            )
        result.append(
            Case(
                id='zeal/maiming/' + label,
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/189',
                ),
                report_contains=('Grand Charm',),
            )
        )
    return tuple(result)


CASES = cases()
