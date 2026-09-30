"""Native Warlord utility remains conditional and does not establish market supply."""

from tests.pricing.knowledge.assessment.item_bank.cases.survival_leveling_sets import Review, cases


REVIEWS = (
    Review(
        "Warlord's Authority",
        'Plated Belt',
        1,
        60,
        ((41, 0, 20), (7, 0, 25 * 256)),
        ('Lightning Resist +20%',),
        "Warlord's Glory",
    ),
    Review("Warlord's Conquest", 'Gauntlets', 1, 60, ((0, 0, 15), (19, 0, 45)), (), "Warlord's Glory"),
    Review(
        "Warlord's Crushers", 'Greaves', 1, 70, ((96, 0, 20), (39, 0, 20)), ('20% Faster Run/Walk',), "Warlord's Glory"
    ),
    Review("Warlord's Lust", 'Great Helm', 1, 63, ((7, 0, 30 * 256),), (), "Warlord's Glory"),
    Review(
        "Warlord's Mantle",
        'Full Plate Mail',
        1,
        80,
        ((16, 0, 25), (43, 0, 30)),
        ('Cold Resist +30%',),
        "Warlord's Glory",
    ),
)

# There is no legal level-zero character. Strength supplies the near-miss boundary.
CASES = tuple(case for case in cases(REVIEWS, prefix='warlord-leveling') if not case.id.endswith('/below-level'))
