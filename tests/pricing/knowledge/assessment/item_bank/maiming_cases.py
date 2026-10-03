"""Equal damage totals must not erase the captured Maiming suffix distinction."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.maiming_report_contracts import maiming_checks
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Grand Charm',
    'magic',
    raw_stats=((19, 0, 49), (22, 0, 10)),
    affix_records=(('prefix', 253), ('suffix', 678)),
    complete=True,
)


def cases(role, case_prefix, player_class, evidence):
    result = []
    for scenario, label, item, context in (
        ('positive', 'native-low-roll', ITEM, {'player_class': player_class}),
        (
            'positive',
            'native-perfect',
            replace(ITEM, raw_stats=((19, 0, 76), (22, 0, 14))),
            {'player_class': player_class},
        ),
        (
            'negative',
            'vita-same-damage',
            replace(
                ITEM,
                raw_stats=((19, 0, 49), (22, 0, 10), (7, 0, 36 * 256)),
                affix_records=(('prefix', 253), ('suffix', 338)),
            ),
            {'player_class': player_class},
        ),
        ('negative', 'unidentified', replace(ITEM, identified=False), {'player_class': player_class}),
        (
            'negative',
            'plain-sharp-same-total',
            replace(ITEM, affix_records=(('prefix', 253),)),
            {'player_class': player_class},
        ),
        ('unknown', 'unread-affixes-same-total', replace(ITEM, affix_records=None), {'player_class': player_class}),
        (
            'negative',
            'below-combined-minimum',
            replace(ITEM, raw_stats=((19, 0, 49), (22, 0, 9))),
            {'player_class': player_class},
        ),
        (
            'unknown',
            'unread-damage',
            replace(ITEM, raw_stats=((19, 0, 49),), complete=False),
            {'player_class': player_class},
        ),
        ('negative', 'wrong-class', ITEM, {'player_class': 'Sorceress'}),
        ('unknown', 'unknown-class', ITEM, {}),
        (
            'negative',
            'ar-global-min',
            replace(ITEM, raw_stats=((19, 0, 6), (22, 0, 3)), affix_records=(('prefix', 218), ('suffix', 678))),
            {'player_class': player_class},
        ),
        (
            'negative',
            'ar-global-max',
            replace(ITEM, raw_stats=((19, 0, 132), (22, 0, 3)), affix_records=(('prefix', 226), ('suffix', 678))),
            {'player_class': player_class},
        ),
        (
            'negative',
            'damage-global-min',
            replace(ITEM, raw_stats=((19, 0, 10), (22, 0, 2)), affix_records=(('prefix', 251), ('suffix', 676))),
            {'player_class': player_class},
        ),
        (
            'negative',
            'damage-low-edge',
            replace(ITEM, raw_stats=((19, 0, 10), (22, 0, 4)), affix_records=(('prefix', 251), ('suffix', 677))),
            {'player_class': player_class},
        ),
        (
            'negative',
            'damage-neutral-edge',
            replace(ITEM, raw_stats=((19, 0, 10), (22, 0, 5)), affix_records=(('prefix', 251), ('suffix', 677))),
            {'player_class': player_class},
        ),
    ):
        truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
        checks = None
        if label in {'native-low-roll', 'native-perfect', 'wrong-class', 'unknown-class'}:
            checks = maiming_checks(
                role, truth, ar=76 if label == 'native-perfect' else 49, damage=14 if label == 'native-perfect' else 10
            )
        elif label.startswith('ar-'):
            checks = maiming_checks(role, truth, ar=item.raw_stats[0][2])
        elif label.startswith('damage-'):
            checks = maiming_checks(role, truth, damage=item.raw_stats[1][2])
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
                    {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in ('19:0', '22:0')}
                )
            )
        result.append(
            Case(
                id=case_prefix + '/' + label,
                report_checks=checks,
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                evidence=(evidence,),
                report_contains=('Grand Charm',),
            )
        )
    return tuple(result)
