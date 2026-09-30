"""The same Enchant item serves independently reviewed uses across builds."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ENCHANT = Item('Tyrant Club', 'unique', 'Demon Limb', ((204, 3351, 1 | (20 << 8)),))
USES = (
    ('dream-paladin', 'Paladin', ('dream-paladin-2-demon-limb-prebuff',)),
    ('strafe-amazon', 'Amazon', ('strafe-amazon-1-demon-limb-prebuff',)),
    (
        'echoing-strike-warlock-guide',
        'Warlock',
        (
            'echoing-strike-warlock-guide-1-demon-limb-prebuff',
            'echoing-strike-warlock-guide-3-demon-limb-prebuff',
        ),
    ),
)


def cases():
    result = []
    for build, klass, roles in USES:
        context = {'player_class': klass, 'player_items': []}
        evidence = (f'pricing/data/wp-a-variants/{build}.json',)
        for label, scenario, item, actual_context, truth in (
            ('positive', 'positive', ENCHANT, context, 'true'),
            ('empty', 'negative', replace(ENCHANT, raw_stats=((204, 3351, 20 << 8),)), context, 'true'),
            ('unread', 'unknown', replace(ENCHANT, raw_stats=()), context, 'true'),
            ('ethereal', 'positive', replace(ENCHANT, ethereal=True), context, 'true'),
            ('full-charges', 'positive', replace(ENCHANT, raw_stats=((204, 3351, 20 | (20 << 8)),)), context, 'true'),
            ('wrong-class', 'negative', ENCHANT, {**context, 'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', 'unknown', ENCHANT, {**context, 'player_class': None}, 'unknown'),
            ('unidentified', 'unknown', replace(ENCHANT, identified=False), context, 'true'),
        ):
            targets = tuple(
                IsPartialDict(
                    id=role,
                    build=build,
                    rule_trace=IsPartialDict(truth=truth),
                    **({'status': 'unknown'} if label == 'unidentified' else {}),
                )
                for role in roles
            )
            expected = {'roles': Contains(*targets)}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {'204:3351': IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))}
                    )
                )
            result.append(
                Case(
                    id=build + '/demon-limb/' + label,
                    item=item,
                    context=actual_context,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=roles,
                    scenario=scenario,
                    evidence=evidence,
                    report_contains=('Demon Limb', 'Enchant') if scenario == 'positive' else (),
                    absent_configurations=() if scenario == 'positive' else tuple(role + '-stats' for role in roles),
                )
            )
    return tuple(result)


CASES = cases()
