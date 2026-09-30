"""Early leech and movement, attack modifiers, and late premium roll boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWS = (
    Review(
        'The Hand of Broc',
        'Leather Gloves',
        102,
        5,
        0,
        0,
        'med',
        'Amazon',
        ((62, 0, 3), (60, 0, 3), (45, 0, 10), (9, 0, 20 * 256)),
        ('3% Mana stolen per hit', '3% Life stolen per hit', '+20 to Mana'),
    ),
    Review(
        'Gorefoot',
        'Heavy Boots',
        108,
        9,
        18,
        0,
        'med',
        'Barbarian',
        ((96, 0, 20), (62, 0, 2), (107, 132, 2), (16, 0, 25)),
        ('20% Faster Run/Walk', '2% Mana stolen per hit', '+2 to Leap (Barbarian Only)'),
    ),
    Review(
        'Treads of Cthon',
        'Chain Boots',
        109,
        15,
        30,
        0,
        'med',
        'Amazon',
        ((96, 0, 30), (32, 0, 50), (7, 0, 10 * 256), (16, 0, 35)),
        ('30% Faster Run/Walk', '+50 Defense vs. Missile', '+10 to Life'),
    ),
    Review(
        'Lava Gout',
        'Battle Gauntlets',
        235,
        42,
        88,
        0,
        'med',
        'Amazon',
        ((39, 0, 24), (118, 0, 1), (198, 52 * 64 + 10, 2), (93, 0, 20), (48, 0, 13), (49, 0, 46)),
        (
            'Fire Resist +24%',
            '2% Chance to cast level 10 Enchant on striking',
            '20% Increased Attack Speed',
            'Adds 13-46 Fire Damage',
        ),
    ),
    Review(
        'Gore Rider',
        'War Boots',
        241,
        47,
        94,
        0,
        'med',
        'Amazon',
        ((91, 0, -25), (141, 0, 15), (96, 0, 30), (136, 0, 15), (135, 0, 10), (16, 0, 180)),
        (
            '15% Deadly Strike',
            '15% Chance of Crushing Blow',
            '10% Chance of Open Wounds',
            '180% (160-200%) Enhanced Defense',
        ),
        trade='med',
    ),
)

CASES = tuple(cases(REVIEWS, prefix='glove-boot-progression'))

# These late items have no dedicated leveling recommendation. Their reviewed
# roll-sensitive trading tiers must survive a missing deciding stat as baseline.
LATE = (
    (
        "Dracul's Grasp",
        'Vampirebone Gloves',
        364,
        ((60, 0, 10), (0, 0, 15), (135, 0, 25), (198, 82 * 64 + 10, 5)),
        (0, 0, 14),
        0,
        ('5% Chance to cast level 10 Life Tap on striking', '25% Chance of Open Wounds'),
    ),
    (
        'Sandstorm Trek',
        'Scarabshell Boots',
        369,
        ((0, 0, 15), (3, 0, 15), (252, 0, 5), (45, 0, 55), (99, 0, 20), (96, 0, 20)),
        (3, 0, 14),
        3,
        ('Repairs 1 durability in 20 seconds', 'Poison Resist +55% (40-70%)', '20% Faster Hit Recovery'),
    ),
    (
        'Shadow Dancer',
        'Myrmidon Greaves',
        309,
        ((2, 0, 25), (188, 49, 2), (96, 0, 30), (99, 0, 30), (91, 0, -20)),
        (2, 0, 24),
        2,
        ('Shadow Disciplines', '30% Faster Run/Walk', '30% Faster Hit Recovery'),
    ),
)


def late_cases():
    for name, base, native, stats, near, missing, snippets in LATE:
        item = Item(base, 'unique', name, stats)
        for label, candidate, tier, scenario in (
            ('premium', item, 'high', 'positive'),
            (
                'near-premium',
                replace(item, raw_stats=(*(s for s in stats if s[0] != near[0]), near)),
                'med',
                'negative',
            ),
            ('missing-roll', replace(item, raw_stats=tuple(s for s in stats if s[0] != missing)), 'med', 'unknown'),
            ('unidentified', replace(item, identified=False), None, 'negative'),
        ):
            yield Case(
                id=f'glove-boot-late/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier), leveling=[]),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=(f'Trade tier: {"mid" if tier == "med" else tier}', *snippets) if tier else (),
                report_absent=('Leveling:',) if tier else ('Trade tier:', 'Leveling:'),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'pricing/knowledge/assessment/rules/named_tiers.json',
                    'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                    'pricing/data/wp-i-uniques-misc.json',
                ),
            )


CASES += tuple(late_cases())


GORE = next(case for case in CASES if case.id.endswith('Gore Rider/equip-level'))
CASES += tuple(
    replace(
        GORE,
        id=f'glove-boot-gore-roll/{ed}',
        item=replace(
            GORE.item,
            raw_stats=tuple(s for s in GORE.item.raw_stats if s[0] != 16) + (((16, 0, ed),) if ed is not None else ()),
        ),
        scenario=scenario,
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=(f'Trade tier: {"mid" if tier == "med" else tier}',),
    )
    for ed, tier, scenario in ((199, 'med', 'negative'), (200, 'high', 'positive'), (None, 'med', 'unknown'))
)

SHADOW = next(case for case in CASES if case.id == 'glove-boot-late/Shadow Dancer/premium')
CASES += tuple(
    replace(
        SHADOW,
        id=f'glove-boot-shadow-skills/{rank}',
        item=replace(SHADOW.item, raw_stats=(*(s for s in SHADOW.item.raw_stats if s[0] != 188), (188, 49, rank))),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='high'), leveling=[]),
            'price_estimate': IsPartialDict(estimate_ist=None),
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 188, 'layer': 49, 'raw': rank},
                        roll_range=IsPartialDict(min=1, max=2),
                        roll_quality=quality,
                    )
                )
            ),
        },
    )
    for rank, quality in ((1, 'low'), (2, 'perfect'))
)

for name in ("Dracul's Grasp", 'Shadow Dancer'):
    premium = next(case for case in CASES if case.id == f'glove-boot-late/{name}/premium')
    for ethereal, scenario in ((True, 'negative'), (None, 'unknown')):
        CASES += (
            replace(
                premium,
                id=f'glove-boot-late/{name}/ethereal-{ethereal}',
                item=replace(premium.item, ethereal=ethereal),
                scenario=scenario,
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='med'), leveling=[]),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=('Trade tier: mid',),
            ),
        )
