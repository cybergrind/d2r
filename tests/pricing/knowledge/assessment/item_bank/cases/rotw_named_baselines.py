"""RotW named baselines exercise distinctive captured properties, not market guesses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Explicit partial captures: the native tables and reviewed tiers are the evidence.
# Opalvein's property-group outcomes are covered in opalvein.py; these baseline
# captures deliberately leave the outcome unknown rather than manufacture it.
REVIEWS = (
    (
        "Ars Al'Diabolos",
        'Blasphemous Grimoire',
        408,
        'high',
        ((188, 58, 2), (201, 77 * 64 + 1, 15), (105, 0, 25), (329, 0, 20), (107, 401, 4)),
        107,
        ('Chaos Skills', '15% Chance to cast level 1 Terror when struck', 'Apocalypse', '(3-5)'),
    ),
    (
        "Ars Tor'Baalos",
        'Blasphemous Compendium',
        409,
        'high',
        (
            (188, 56, 2),
            (201, 87 * 64 + 1, 15),
            (107, 374, 3),
            (107, 380, 3),
            (107, 379, 2),
            (107, 381, 2),
            (216, 0, 12 * 256),
            (36, 0, 7),
        ),
        107,
        (
            'Demon Skills',
            'Demonic Mastery',
            'Blood Boil',
            'Engorge',
            'Consume',
            '+120 to Life (Based on Character Level)',
        ),
    ),
    (
        "Ars Dul'Mephistos",
        'Occult Tome',
        410,
        'high',
        (
            (83, 7, 2),
            (201, 59 * 64 + 28, 15),
            (105, 0, 25),
            (99, 0, 30),
            (17, 0, 90),
            (18, 0, 90),
            (119, 0, 60),
            (358, 0, 15),
        ),
        358,
        (
            '+2 to Warlock Skill Levels',
            '15% Chance to cast level 28 Blizzard when struck',
            '90% (70-115%) Enhanced Damage',
            'Enemy Magic Resistance',
        ),
    ),
    (
        'Measured Wrath',
        'Burnt Text',
        411,
        'med',
        ((83, 7, 1), (201, 394 * 64 + 25, 5), (105, 0, 25), (107, 376, 2), (107, 394, 2), (107, 398, 2)),
        107,
        (
            '+1 to Warlock Skill Levels',
            '5% Chance to cast level 25 Ring of Fire when struck',
            'Summon Tainted',
            'Flame Wave',
        ),
    ),
    (
        'Wraithstep',
        'Mirrored Boots',
        413,
        'high',
        ((188, 57, 1), (96, 0, 30), (99, 0, 20), (2, 0, 12), (1, 0, 12)),
        188,
        ('Eldritch Skills', '30% Faster Run/Walk', '20% Faster Hit Recovery'),
    ),
    (
        'Bloodpact Shard',
        'Mithral Point',
        414,
        'med',
        ((127, 0, 1), (105, 0, 30), (76, 0, 12), (107, 378, 3), (107, 380, 2), (107, 382, 2), (150, 0, 25)),
        107,
        ('+1 to All Skills', '30% Faster Cast Rate', 'Blood Oath', 'Blood Boil', 'Bind Demon', 'Slows Target by 25%'),
    ),
    (
        'Sling',
        'Ring',
        415,
        'high',
        ((97, 411, 1), (105, 0, 10), (358, 0, 4), (1, 0, 12), (150, 0, 15), (80, 0, 15)),
        358,
        ('Town Portal', '10% Faster Cast Rate', 'Enemy Magic Resistance', 'Slows Target by 15%'),
    ),
    (
        'Opalvein',
        'Ring',
        416,
        'high',
        ((195, 398 * 64 + 15, 2), (105, 0, 10), (39, 0, 7), (41, 0, 7), (43, 0, 7), (45, 0, 7), (138, 0, 2)),
        105,
        (
            '2% Chance to cast level 15 Flame Wave on attack',
            'Fire Resist +7% (6-8%)',
            '+2 (1-3) to Mana after each Kill',
        ),
    ),
    (
        'Entropy Locket',
        'Amulet',
        417,
        'high',
        ((198, 399 * 64 + 19, 4), (357, 0, 8), (105, 0, 7), (41, 0, 35), (77, 0, 12), (35, 0, 10)),
        357,
        (
            '4% Chance to cast level 19 Miasma Chain on striking',
            'Magic Skill Damage',
            'Lightning Resist +35% (25-40%)',
        ),
    ),
    (
        "Gheed's Wager",
        'Troll Belt',
        418,
        'high',
        ((105, 0, 15), (99, 0, 15), (96, 0, 15), (16, 0, 120), (358, 0, 5), (79, 0, 60)),
        358,
        ('15% (10-20%) Faster Cast Rate', '15% (10-20%) Faster Hit Recovery', '120% (90-150%) Enhanced Defense'),
    ),
    (
        "Hellwarden's Will",
        'Death Mask',
        419,
        'med',
        ((127, 0, 1), (333, 0, 7), (358, 0, 7), (105, 0, 20), (93, 0, 20)),
        333,
        (
            '+1 to All Skills',
            '20% Faster Cast Rate',
            '20% Increased Attack Speed',
            'Enemy Fire Resistance',
            'Enemy Magic Resistance',
        ),
    ),
    (
        "Guardian's Thunder",
        'Colossal Jewel',
        421,
        'high',
        ((201, 235 * 64 + 25, 1), (330, 0, 8), (50, 0, 1), (51, 0, 75), (334, 0, 8), (85, 0, 4)),
        334,
        ('1% Chance to cast level 25 Cyclone Armor when struck', 'Adds 1-75 Lightning Damage', '(5-10%)'),
    ),
    (
        "Defender's Fire",
        'Colossal Jewel',
        423,
        'high',
        ((201, 46 * 64 + 25, 1), (329, 0, 8), (48, 0, 20), (49, 0, 60), (333, 0, 8), (85, 0, 4)),
        333,
        ('1% Chance to cast level 25 Blaze when struck', 'Adds 20-60 Fire Damage', '(5-10%)'),
    ),
    (
        "Protector's Stone",
        'Colossal Jewel',
        424,
        'high',
        ((201, 267 * 64 + 15, 1), (17, 0, 40), (18, 0, 40), (366, 0, 8), (85, 0, 4)),
        366,
        (
            '1% Chance to cast level 15 Fade when struck',
            '40% (30-50%) Enhanced Damage',
            'Enemy Physical Damage Resistance',
        ),
    ),
    (
        "Guardian's Light",
        'Colossal Jewel',
        425,
        'med',
        ((201, 387 * 64 + 25, 1), (357, 0, 8), (52, 0, 15), (53, 0, 35), (358, 0, 8), (85, 0, 4)),
        358,
        ('1% Chance to cast level 25 Psychic Ward when struck', 'Adds 15-35 Magic Damage', 'Enemy Magic Resistance'),
    ),
)


def cases():
    for name, base, native, tier, stats, missing, snippets in REVIEWS:
        item = Item(base, 'unique', name, stats, viewer_level=80, named_table_id=native)
        for label, candidate, expected_tier, scenario in (
            ('observed', item, tier, 'positive'),
            ('missing-stat', replace(item, raw_stats=tuple(s for s in stats if s[0] != missing)), tier, 'unknown'),
            ('unidentified', replace(item, identified=False), None, 'negative'),
        ):
            yield Case(
                id=f'rotw-named-baseline/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=expected_tier), leveling=[]),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=snippets if label == 'observed' else (),
                report_absent=('Leveling:', 'no roll bucket', '  no roll\n')
                if expected_tier
                else ('Trade tier:', 'Leveling:', 'no roll bucket', '  no roll\n'),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'third-parties/d2data/json/skills.json',
                    'pricing/knowledge/assessment/rules/named_tiers.json',
                    'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                ),
            )


CASES = tuple(cases())


AL = next(case for case in CASES if case.id == "rotw-named-baseline/Ars Al'Diabolos/observed")
CASES += tuple(
    replace(
        AL,
        id=f'rotw-named-baseline/Ars Al/Apocalypse-{rank}',
        item=replace(AL.item, raw_stats=(*(s for s in AL.item.raw_stats if s[0] != 107), (107, 401, rank))),
        expected={
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 107, 'layer': 401, 'raw': rank},
                        roll_range=IsPartialDict(min=3, max=5),
                        roll_quality=quality,
                    )
                )
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
    )
    for rank, quality in ((3, 'low'), (5, 'perfect'))
)

WRAITH = next(case for case in CASES if case.id == 'rotw-named-baseline/Wraithstep/observed')
CASES += tuple(
    replace(
        WRAITH,
        id=f'rotw-named-baseline/Wraithstep/tree-{layer}',
        item=replace(WRAITH.item, raw_stats=(*(s for s in WRAITH.item.raw_stats if s[0] != 188), (188, layer, 1))),
        report_contains=(f'+1 to {tree} Skills (Warlock Only)', 'Trade tier: high'),
    )
    for layer, tree in ((56, 'Demon'), (57, 'Eldritch'), (58, 'Chaos'))
)

HELL = next(case for case in CASES if case.id == "rotw-named-baseline/Hellwarden's Will/observed")
CASES += tuple(
    replace(
        HELL,
        id=f'rotw-named-baseline/Hellwarden/pierce-8-{magic}',
        item=replace(
            HELL.item,
            raw_stats=(
                *(s for s in HELL.item.raw_stats if s[0] not in (333, 358)),
                (333, 0, 8),
                (358, 0, magic),
                (16, 0, 180),
            ),
        ),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier), leveling=[]),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=(f'Trade tier: {"mid" if tier == "med" else tier}',),
    )
    for magic, tier in ((7, 'med'), (8, 'high'))
)


HELL_PERFECT = next(case for case in CASES if case.id == 'rotw-named-baseline/Hellwarden/pierce-8-8')
CASES += (
    replace(
        HELL_PERFECT,
        id='rotw-named-baseline/Hellwarden/perfect-pierce-unknown-defense',
        item=replace(HELL_PERFECT.item, raw_stats=tuple(s for s in HELL_PERFECT.item.raw_stats if s[0] != 16)),
        scenario='unknown',
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='med'), leveling=[]),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=('Trade tier: mid',),
    ),
)
