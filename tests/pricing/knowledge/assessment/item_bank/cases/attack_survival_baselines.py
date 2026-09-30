"""Attack utility and survival remain distinct from ordinary resale tiers."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases


REVIEWS = (
    Review(
        'String of Ears',
        'Demonhide Sash',
        242,
        29,
        20,
        0,
        'med',
        'Amazon',
        ((36, 0, 12), (35, 0, 13), (60, 0, 7), (16, 0, 165)),
        ('12% (10-15%)', '7% (6-8%) Life stolen per hit', '165% (150-180%) Enhanced Defense'),
    ),
    Review(
        'Razortail',
        'Sharkskin Belt',
        243,
        32,
        20,
        0,
        'med',
        'Amazon',
        ((156, 0, 33), (2, 0, 15), (22, 0, 10), (16, 0, 135)),
        ('33% Piercing Attack', '+15 to Dexterity', '135% (120-150%) Enhanced Defense'),
    ),
    Review(
        'Twitchthroe',
        'Studded Leather',
        82,
        16,
        27,
        0,
        'high',
        'Amazon',
        ((93, 0, 20), (99, 0, 20), (20, 0, 25), (0, 0, 10), (2, 0, 10)),
        ('20% Increased Attack Speed', '20% Faster Hit Recovery', '25% Increased Chance of Blocking'),
    ),
)

CASES = tuple(cases(REVIEWS, prefix='attack-survival-baseline'))


STRING = next(case for case in CASES if case.id.endswith('String of Ears/equip-level'))
CASES += tuple(
    replace(
        STRING,
        id=f'attack-survival-roll/{stat}/{value}',
        item=replace(
            STRING.item,
            raw_stats=tuple(s for s in STRING.item.raw_stats if s[0] != stat)
            + (((stat, 0, value),) if value is not None else ()),
        ),
        scenario=scenario,
        expected={
            'price_estimate': IsPartialDict(estimate_ist=None),
            **(
                {
                    'extraction': IsPartialDict(
                        decoded_stats=Contains(
                            IsPartialDict(
                                memory_stat={'id': stat, 'layer': 0, 'raw': value},
                                roll_quality=quality,
                                roll_range=IsPartialDict(min=minimum, max=maximum),
                            )
                        )
                    )
                }
                if value is not None
                else {
                    'extraction': IsPartialDict(
                        decoded_stats=FunctionCheck(
                            lambda rows, absent=stat: all(
                                row.get('memory_stat', {}).get('id') != absent for row in rows
                            )
                        )
                    )
                }
            ),
        },
        report_contains=(),
        report_absent=(),
    )
    for stat, minimum, maximum, label in (
        (36, 10, 15, 'Physical Damage Received Reduced'),
        (35, 10, 15, 'Magic Damage Reduced'),
        (60, 6, 8, 'Life stolen per hit'),
        (16, 150, 180, 'Enhanced Defense'),
    )
    for value, quality, scenario in (
        (minimum, 'low', 'negative'),
        (maximum, 'perfect', 'positive'),
        (None, None, 'unknown'),
    )
)
