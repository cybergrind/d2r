"""Progression set pieces distinguish farming, movement, casting and attack uses."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.survival_leveling_sets import Review, cases


REVIEWS = (
    Review(
        "Sander's Paragon",
        'Cap',
        25,
        0,
        ((80, 0, 35), (78, 0, 8)),
        ('35% Better Chance of Getting Magic Items',),
        leveling='low',
    ),
    Review(
        "Sander's Riprap",
        'Heavy Boots',
        20,
        18,
        ((96, 0, 40), (19, 0, 100), (0, 0, 5), (2, 0, 10)),
        ('40% Faster Run/Walk',),
        leveling='high',
    ),
    Review(
        "Sander's Superstition",
        'Bone Wand',
        25,
        0,
        ((105, 0, 20), (9, 0, 25 * 256)),
        ('20% Faster Cast Rate',),
        "Sander's Folly",
        leveling='high',
    ),
    Review("Sander's Taboo", 'Heavy Gloves', 28, 0, ((93, 0, 20), (7, 0, 40 * 256)), ('20% Increased Attack Speed',)),
    Review(
        "Sigon's Guard",
        'Tower Shield',
        6,
        75,
        ((127, 0, 1), (20, 0, 20)),
        ('+1 to All Skills',),
        "Sigon's Complete Steel",
        leveling='high',
    ),
    Review(
        "Sigon's Shelter",
        'Gothic Plate',
        6,
        70,
        ((16, 0, 25), (41, 0, 30)),
        ('Lightning Resist +30%',),
        "Sigon's Complete Steel",
        leveling='high',
    ),
    Review(
        "Magnus' Skin",
        'Sharkskin Gloves',
        37,
        20,
        ((93, 0, 20), (19, 0, 100), (39, 0, 15)),
        ('20% Increased Attack Speed', 'Fire Resist +15%'),
    ),
    Review(
        'Telling of Beads',
        'Amulet',
        30,
        0,
        ((127, 0, 1), (43, 0, 18), (45, 0, 40)),
        ('+1 to All Skills', 'Cold Resist +18%'),
    ),
    Review(
        "Trang-Oul's Claws",
        'Heavy Bracers',
        45,
        58,
        ((105, 0, 20), (43, 0, 30)),
        ('20% Faster Cast Rate', 'Cold Resist +30%'),
        player_class='Necromancer',
    ),
    Review("Vidala's Fetlock", 'Light Plated Boots', 14, 50, ((96, 0, 30),), ('30% Faster Run/Walk',)),
)


def with_sources(case):
    # Native table names differ from the localized Sander display identities.
    native = case.item.name.replace("Sander's", "McAuley's")
    return replace(
        case,
        evidence=(
            f'third-parties/d2data/json/setitems.json:/{native}',
            'third-parties/d2data/json/armor.json',
            'third-parties/d2data/json/weapons.json',
            'pricing/data/appraisal-recommendations.json',
            f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:set:{case.item.name}',
            'pricing/knowledge/assessment/rules/named_baselines.json',
        ),
    )


CASES = tuple(with_sources(case) for case in cases(REVIEWS, prefix='progression-leveling-set'))
