"""Utility melee uniques: class bonuses, recovery denial, slow and magic damage."""

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases


REVIEWS = (
    Review(
        'Fleshrender',
        'Barbed Club',
        147,
        38,
        30,
        0,
        'med',
        'Druid',
        ((135, 0, 25), (117, 0, 1), (136, 0, 20), (141, 0, 20), (83, 5, 1), (188, 41, 2)),
        (
            '25% Chance of Open Wounds',
            'Prevent Monster Heal',
            '20% Chance of Crushing Blow',
            '20% Deadly Strike',
            '+1 to Druid Skill Levels',
            'Shape Shifting Skills',
        ),
    ),
    Review(
        "Ginther's Rift",
        'Dimensional Blade',
        158,
        37,
        85,
        60,
        'med',
        'Barbarian',
        ((35, 0, 9), (93, 0, 30), (252, 0, 20), (52, 0, 50), (53, 0, 120), (17, 0, 125), (18, 0, 125)),
        (
            '30% Increased Attack Speed',
            'Repairs 1 durability in 5 seconds',
            'Adds 50-120 Magic Damage',
            '125% (100-150%) Enhanced Damage',
        ),
    ),
    Review(
        'The Atlantean',
        'Ancient Sword',
        161,
        42,
        127,
        88,
        'med',
        'Paladin',
        ((0, 0, 16), (2, 0, 12), (3, 0, 8), (17, 0, 225), (18, 0, 225), (83, 3, 2), (119, 0, 50)),
        ('+2 to Paladin Skill Levels', '50% Bonus to Attack Rating', '225% (200-250%) Enhanced Damage'),
    ),
    Review(
        "The General's Tan Do Li Ga",
        'Flail',
        21,
        21,
        41,
        35,
        'med',
        'Paladin',
        ((150, 0, 50), (62, 0, 5), (17, 0, 55), (18, 0, 55), (93, 0, 20)),
        ('Slows Target by 50%', '5% Mana stolen per hit', '20% Increased Attack Speed', '55% (50-60%) Enhanced Damage'),
    ),
)

CASES = tuple(cases(REVIEWS, prefix='melee-utility-baseline'))
