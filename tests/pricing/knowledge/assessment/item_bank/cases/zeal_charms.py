"""Guide charm combinations exercised through native decoding and appraisal."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Independently transcribed lower native rolls; no imports from rule templates.
EXAMPLES = (
    ('grand-sharp-vita', 'Grand Charm', 185, ((19, 49), (22, 7), (7, 41))),
    ('grand-steel-vita', 'Grand Charm', 186, ((19, 118), (7, 41))),
    ('grand-sharp-balance', 'Grand Charm', 187, ((19, 49), (22, 7), (99, 12))),
    ('grand-steel-balance', 'Grand Charm', 188, ((19, 118), (99, 12))),
    ('grand-sharp', 'Grand Charm', 190, ((19, 49), (22, 7))),
    ('grand-steel', 'Grand Charm', 191, ((19, 118),)),
    ('grand-shimmering-balance', 'Grand Charm', 192, ((39, 13), (41, 13), (43, 13), (45, 13), (99, 12))),
    ('grand-shimmering', 'Grand Charm', 193, ((39, 13), (41, 13), (43, 13), (45, 13))),
    ('fine-good-luck', 'Small Charm', 173, ((19, 10), (22, 1), (80, 6))),
    ('steel-good-luck', 'Small Charm', 174, ((19, 25), (80, 6))),
    ('fine-vita', 'Small Charm', 175, ((19, 10), (22, 1), (7, 16))),
    ('fine-balance', 'Small Charm', 176, ((19, 10), (22, 1), (99, 5))),
    ('shimmering-good-luck', 'Small Charm', 177, ((39, 3), (41, 3), (43, 3), (45, 3), (80, 6))),
    ('shimmering-vita', 'Small Charm', 178, ((39, 3), (41, 3), (43, 3), (45, 3), (7, 16))),
    ('fine', 'Small Charm', 179, ((19, 10), (22, 1))),
    ('good-luck', 'Small Charm', 180, ((80, 6),)),
    ('vita', 'Small Charm', 181, ((7, 16),)),
    ('shimmering', 'Small Charm', 182, ((39, 3), (41, 3), (43, 3), (45, 3))),
    ('sharp-large-vita', 'Large Charm', 184, ((19, 21), (22, 4), (7, 31))),
)


LOWER_TIERS = {
    'grand-steel': (((19, 88),), 0),
    'grand-steel-vita': (((19, 88), (7, 36)), 1),
    'grand-steel-balance': (((19, 88), (99, 12)), 0),
    'grand-sharp-vita': (((19, 49), (22, 7), (7, 36)), 2),
    'sharp-large-vita': (((19, 21), (22, 4), (7, 26)), 2),
}


def lower_scenarios(slug, item):
    if slug not in LOWER_TIERS:
        return ()
    stats, boundary = LOWER_TIERS[slug]
    raw = tuple((key, 0, value * 256 if key == 7 else value) for key, value in stats)
    below = tuple(
        (key, layer, value - (256 if key == 7 else 1)) if index == boundary else (key, layer, value)
        for index, (key, layer, value) in enumerate(raw)
    )
    return (
        ('positive', 'lower-named-tier', replace(item, raw_stats=raw), {'player_class': 'Paladin'}),
        ('negative', 'below-named-tier', replace(item, raw_stats=below), {'player_class': 'Paladin'}),
    )


def cases():
    result = []
    for slug, base, span, stats in EXAMPLES:
        role = f'zeal-paladin-charm-{slug}'
        raw = tuple((key, 0, value * 256 if key == 7 else value) for key, value in stats)
        item = Item(base, 'magic', raw_stats=raw)
        for scenario, label, candidate, context in (
            *lower_scenarios(slug, item),
            ('positive', 'low-rolls', item, {'player_class': 'Paladin'}),
            ('negative', 'wrong-class', item, {'player_class': 'Sorceress'}),
            ('unknown', 'unknown-class', item, {}),
            (
                'negative',
                'missing-modifier',
                replace(item, raw_stats=raw[1:], complete=True),
                {'player_class': 'Paladin'},
            ),
            ('unknown', 'unread-modifier', replace(item, raw_stats=raw[1:]), {'player_class': 'Paladin'}),
            (
                'negative',
                'wrong-size',
                replace(item, base='Small Charm' if base == 'Grand Charm' else 'Grand Charm'),
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
            if label == 'wrong-size':
                # Type routing excludes this role before predicate evaluation.
                # absent_configurations below verifies no charm contribution leaks.
                expected = {'family': 'charm'}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {f'{key}:0': IsPartialDict(configuration_ids=Contains(role + '-stats')) for key, _ in stats}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/charms/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(candidate.base,),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
