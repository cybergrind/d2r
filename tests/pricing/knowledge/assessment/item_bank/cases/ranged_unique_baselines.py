"""Ranged progression: arrow effects, pierce, cold damage and native sockets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case


REVIEWS = (
    Review(
        'Buriza-Do Kyanon',
        'Ballista',
        198,
        41,
        110,
        80,
        'high',
        'Amazon',
        ((156, 0, 100), (93, 0, 80), (134, 0, 3), (54, 0, 32), (55, 0, 196), (56, 0, 200), (17, 0, 175), (18, 0, 175)),
        (
            '100% Piercing Attack',
            '80% Increased Attack Speed',
            'Freezes target +3',
            'Adds 32-196 Cold Damage',
            '(150-200%)',
        ),
    ),
    Review(
        'Demon Machine',
        'Chu-Ko-Nu',
        199,
        49,
        80,
        95,
        'high',
        'Sorceress',
        ((156, 0, 66), (158, 0, 6), (9, 0, 36 * 256), (19, 0, 632), (17, 0, 123), (18, 0, 123)),
        ('66% Piercing Attack', 'Fires Explosive Arrows or Bolts (Level 6)', '+36 to Mana', '123% Enhanced Damage'),
    ),
    Review(
        'Goldstrike Arch',
        'Gothic Bow',
        195,
        46,
        95,
        118,
        'med',
        'Amazon',
        ((93, 0, 50), (198, 121 * 64 + 7, 5), (121, 0, 150), (122, 0, 150), (17, 0, 225), (18, 0, 225)),
        ('50% Increased Attack Speed', '5% Chance to cast level 7 Fist of the Heavens on striking', '(200-250%)'),
    ),
    Review(
        'Raven Claw',
        'Long Bow',
        61,
        15,
        22,
        19,
        'high',
        'Sorceress',
        ((158, 0, 3), (119, 0, 50), (17, 0, 65), (18, 0, 65)),
        ('Fires Explosive Arrows or Bolts (Level 3)', '50% Bonus to Attack Rating', '(60-70%)'),
    ),
    Review(
        "Rogue's Bow",
        'Composite Bow',
        62,
        20,
        25,
        35,
        'med',
        'Amazon',
        ((141, 0, 30), (93, 0, 50), (39, 0, 10), (17, 0, 50), (18, 0, 50)),
        ('30% Deadly Strike', '50% Increased Attack Speed', 'Fire Resist +10%', '(40-60%)'),
    ),
    Review(
        'Witchwild String',
        'Short Siege Bow',
        192,
        39,
        65,
        80,
        'med',
        'Amazon',
        ((198, 66 * 64 + 5, 2), (250, 0, 8), (157, 0, 20), (39, 0, 40), (194, 0, 2), (17, 0, 160), (18, 0, 160)),
        (
            '2% Chance to cast level 5 Amplify Damage on striking',
            '39% Deadly Strike (Based on Character Level)',
            'Fires Magic Arrows (Level 20)',
            'Sockets: 2 — 2 empty',
            '(150-170%)',
        ),
    ),
    Review(
        'Wizendraw',
        'Long Battle Bow',
        64,
        26,
        40,
        50,
        'med',
        'Amazon',
        ((157, 0, 5), (335, 0, 28), (93, 0, 20), (17, 0, 75), (18, 0, 75)),
        ('Fires Magic Arrows (Level 5)', 'Enemy Cold Resistance', '(20-35%)', '20% Increased Attack Speed'),
    ),
)


CASES = tuple(
    replace(case, item=replace(case.item, sockets=2, viewer_level=39)) if case.item.name == 'Witchwild String' else case
    for case in cases(REVIEWS, prefix='ranged-unique-baseline')
)


WIZENDRAW = next(case for case in CASES if case.id.endswith('Wizendraw/equip-level'))
CASES += tuple(
    Case(
        id=f'wizendraw-cold-roll/{value}',
        item=replace(
            WIZENDRAW.item,
            raw_stats=tuple(s for s in WIZENDRAW.item.raw_stats if s[0] != 335)
            + (((335, 0, value),) if value is not None else ()),
        ),
        context=WIZENDRAW.context,
        scenario=scenario,
        covers=('named:unique:Wizendraw',),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='low')),
            'price_estimate': IsPartialDict(estimate_ist=None),
            **(
                {
                    'extraction': IsPartialDict(
                        decoded_stats=Contains(
                            IsPartialDict(
                                memory_stat={'id': 335, 'layer': 0, 'raw': value},
                                roll_quality=quality,
                                roll_range=IsPartialDict(min=20, max=35),
                            )
                        )
                    )
                }
                if value is not None
                else {}
            ),
        },
        report_contains=('Trade tier: low',),
        report_absent=('Enemy Cold Resistance',) if value is None else (),
        evidence=(*WIZENDRAW.evidence, 'third-parties/d2data/json/properties.json:/pierce-cold'),
    )
    for value, quality, scenario in ((20, 'low', 'negative'), (35, 'perfect', 'positive'), (None, None, 'unknown'))
)
