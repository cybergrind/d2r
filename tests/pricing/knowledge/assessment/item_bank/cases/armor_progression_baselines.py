"""Armor progression retains defensive and caster utility across wearer contexts."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases


REVIEWS = (
    Review(
        'Rockfleece',
        'Field Plate',
        89,
        28,
        50,
        0,
        'med',
        'Paladin',
        ((91, 0, -10), (16, 0, 115), (36, 0, 10), (34, 0, 5), (0, 0, 5)),
        ('Requirements -10%', '115% (100-130%) Enhanced Defense', 'Physical Damage Received Reduced by 10%'),
    ),
    Review(
        'Rockstopper',
        'Sallet',
        202,
        31,
        43,
        0,
        'med',
        'Paladin',
        ((41, 0, 30), (39, 0, 35), (43, 0, 30), (36, 0, 10), (99, 0, 30), (3, 0, 15)),
        (
            'Lightning Resist +30% (20-40%)',
            'Fire Resist +35% (20-50%)',
            'Cold Resist +30% (20-40%)',
            '30% Faster Hit Recovery',
        ),
    ),
    Review(
        'Undead Crown',
        'Crown',
        77,
        29,
        55,
        0,
        'med',
        'Necromancer',
        ((60, 0, 5), (45, 0, 50), (118, 0, 1), (107, 69, 3), (16, 0, 45)),
        ('5% Life stolen per hit', 'Poison Resist +50%', 'Half Freeze Duration', 'Skeleton Mastery'),
        side='merc',
    ),
    Review(
        'Duskdeep',
        'Full Helm',
        74,
        17,
        41,
        0,
        'med',
        'Paladin',
        ((39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15), (34, 0, 7), (16, 0, 40)),
        ('Fire Resist +15%', 'Damage Reduced by 7', '40% (30-50%) Enhanced Defense'),
    ),
    Review(
        'Rattlecage',
        'Gothic Plate',
        90,
        29,
        70,
        0,
        'med',
        'Paladin',
        ((112, 0, 52), (19, 0, 45), (136, 0, 25)),
        ('Hit Causes Monster to Flee +40%', '25% Chance of Crushing Blow'),
    ),
    Review(
        'Skin of the Flayed One',
        'Demonhide Armor',
        211,
        31,
        50,
        0,
        'med',
        'Necromancer',
        ((252, 0, 10), (74, 0, 20), (60, 0, 6), (16, 0, 170)),
        ('Repairs 1 durability in 10 seconds', '6% (5-7%) Life stolen per hit', '170% (150-190%) Enhanced Defense'),
        side='merc',
    ),
    Review(
        'Silks of the Victor',
        'Ancient Armor',
        92,
        28,
        100,
        0,
        'med',
        'Sorceress',
        ((62, 0, 5), (127, 0, 1), (16, 0, 110)),
        ('5% Mana stolen per hit', '+1 to All Skills', '110% (100-120%) Enhanced Defense'),
    ),
    Review(
        "Que-Hegan's Wisdom",
        'Mage Plate',
        223,
        51,
        55,
        0,
        'med',
        'Sorceress',
        ((105, 0, 20), (138, 0, 3), (35, 0, 8), (99, 0, 20), (127, 0, 1)),
        ('20% Faster Cast Rate', '+3 to Mana after each Kill', '20% Faster Hit Recovery', '+1 to All Skills'),
    ),
)

CASES = tuple(cases(REVIEWS, prefix='armor-progression-baseline'))
CASES += tuple(
    cases(
        tuple(replace(review, side='merc') for review in REVIEWS if review.name in ('Duskdeep', 'Rockstopper')),
        prefix='armor-progression-merc',
    )
)


ROCKSTOPPER = next(case for case in CASES if case.id.endswith('Rockstopper/equip-level'))
CASES += tuple(
    replace(
        ROCKSTOPPER,
        id=f'armor-progression-roll/Rockstopper/{stat}/{value}',
        item=replace(
            ROCKSTOPPER.item,
            raw_stats=tuple(s for s in ROCKSTOPPER.item.raw_stats if s[0] != stat)
            + (((stat, 0, value),) if value is not None else ()),
        ),
        scenario=scenario,
        expected={
            'price_estimate': IsPartialDict(estimate_ist=None),
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': stat, 'layer': 0, 'raw': value},
                        roll_range=IsPartialDict(min=minimum, max=maximum),
                        roll_quality=quality,
                    )
                )
                if value is not None
                else FunctionCheck(
                    lambda rows, absent=stat: all(row.get('memory_stat', {}).get('id') != absent for row in rows)
                )
            ),
        },
        report_contains=(),
    )
    for stat, minimum, maximum in ((39, 20, 50), (41, 20, 40), (43, 20, 40))
    for value, quality, scenario in (
        (minimum, 'low', 'negative'),
        (maximum, 'perfect', 'positive'),
        (None, None, 'unknown'),
    )
)
