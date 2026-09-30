"""Class staples retain native skills, rolls and separate leveling/trade tiers."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case


REVIEWS = (
    Review(
        "Titan's Revenge",
        'Ceremonial Javelin',
        281,
        42,
        25,
        109,
        'high',
        'Amazon',
        ((83, 0, 2), (188, 2, 2), (17, 0, 175), (18, 0, 175), (60, 0, 7), (96, 0, 30)),
        ('+2 to Amazon Skill Levels', 'Javelin and Spear Skills', '(150-200%)', '7% (5-9%) Life stolen per hit'),
        trade='med',
    ),
    Review(
        "Arreat's Face",
        'Slayer Guard',
        279,
        42,
        118,
        0,
        'high',
        'Barbarian',
        ((83, 4, 2), (188, 32, 2), (16, 0, 175), (60, 0, 4), (99, 0, 30)),
        ('+2 to Barbarian Skill Levels', 'Combat Skills', '(150-200%)', '4% (3-6%) Life stolen per hit'),
        trade='med',
    ),
    Review(
        "Jalal's Mane",
        'Totemic Mask',
        287,
        42,
        65,
        0,
        'high',
        'Druid',
        ((83, 5, 2), (188, 41, 2), (99, 0, 30), (138, 0, 5), (16, 0, 175)),
        ('+2 to Druid Skill Levels', 'Shape Shifting Skills', '30% Faster Hit Recovery', '(150-200%)'),
    ),
    Review(
        'Herald of Zakarum',
        'Gilded Shield',
        285,
        42,
        89,
        0,
        'med',
        'Paladin',
        ((83, 3, 2), (188, 24, 2), (102, 0, 30), (16, 0, 175), (39, 0, 50)),
        ('+2 to Paladin Skill Levels', 'Combat Skills', '30% Faster Block Rate', '(150-200%)'),
        trade='med',
    ),
    Review(
        'The Oculus',
        'Swirling Crystal',
        284,
        42,
        0,
        0,
        'med',
        'Sorceress',
        ((83, 1, 3), (105, 0, 30), (80, 0, 50), (201, 54 * 64 + 1, 25), (138, 0, 5)),
        (
            '+3 to Sorceress Skill Levels',
            '30% Faster Cast Rate',
            '50% Better Chance of Getting Magic Items',
            '25% Chance to cast level 1 Teleport when struck',
        ),
    ),
    Review(
        'Homunculus',
        'Heirophant Trophy',
        280,
        42,
        58,
        0,
        'high',
        'Necromancer',
        ((83, 2, 2), (188, 16, 2), (102, 0, 30), (27, 0, 33), (16, 0, 175)),
        ('+2 to Necromancer Skill Levels', 'Curses', 'Regenerate Mana 33%', '(150-200%)'),
        trade='med',
    ),
    Review(
        "Bartuc's Cut-Throat",
        'Greater Talons',
        286,
        42,
        79,
        79,
        'med',
        'Assassin',
        ((83, 6, 2), (188, 50, 1), (99, 0, 30), (60, 0, 7), (17, 0, 175), (18, 0, 175)),
        ('+2 to Assassin Skill Levels', 'Martial Arts', '30% Faster Hit Recovery', '(150-200%)'),
    ),
    Review(
        "Lycander's Aim",
        'Ceremonial Bow',
        282,
        42,
        73,
        110,
        'med',
        'Amazon',
        ((83, 0, 2), (188, 0, 2), (93, 0, 20), (62, 0, 6), (17, 0, 175), (18, 0, 175)),
        (
            '+2 to Amazon Skill Levels',
            'Bow and Crossbow Skills',
            '20% Increased Attack Speed',
            '6% (5-8%) Mana stolen per hit',
            '(150-200%)',
        ),
    ),
)


CASES = tuple(cases(REVIEWS, prefix='class-unique-progression'))

# The reviewed tier is mid from170 ED, including the higher >=190 price band.
# A perfect stat roll is distinct from a high trade tier or a numerical estimate.
HERALD = next(case for case in CASES if case.id.endswith('Herald of Zakarum/equip-level'))
CASES += tuple(
    Case(
        id=f'class-shield-ed/{value}',
        item=replace(
            HERALD.item,
            raw_stats=tuple(s for s in HERALD.item.raw_stats if s[0] != 16)
            + (((16, 0, value),) if value is not None else ()),
        ),
        context=HERALD.context,
        scenario=scenario,
        covers=('named:unique:Herald of Zakarum',),
        expected={
            'assessment': IsPartialDict(
                trade_tier=IsPartialDict(tier=tier, baseline=IsPartialDict(tier='low')),
                leveling=Contains(IsPartialDict(tier='med')),
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
            **(
                {
                    'extraction': IsPartialDict(
                        decoded_stats=Contains(
                            IsPartialDict(
                                memory_stat={'id': 16, 'layer': 0, 'raw': value},
                                roll_quality='perfect' if value == 200 else 'low' if value == 150 else 'normal',
                            )
                        )
                    )
                }
                if value is not None
                else {}
            ),
        },
        report_contains=(f'Trade tier: {"mid" if tier == "med" else tier}',),
        evidence=(*HERALD.evidence, 'pricing/data/wp-i-uniques-misc.json:/UQ-herald-of-zakarum'),
    )
    for value, tier, scenario in (
        (169, 'low', 'negative'),
        (170, 'med', 'positive'),
        (189, 'med', 'negative'),
        (190, 'med', 'positive'),
        (200, 'med', 'positive'),
        (150, 'low', 'negative'),
        (None, 'low', 'unknown'),
    )
)
