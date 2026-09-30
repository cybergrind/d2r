"""Mercenary progression weapons retain slow, crushing blow and sustain utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases


REVIEWS = (
    Review(
        'Kelpie Snare',
        'Fuscina',
        173,
        33,
        77,
        25,
        'high',
        'Necromancer',
        ((150, 0, 75), (39, 0, 50), (0, 0, 10), (17, 0, 160), (18, 0, 160)),
        ('Slows Target by 75%', 'Fire Resist +50%', '160% (140-180%) Enhanced Damage'),
        side='merc',
    ),
    Review(
        'Hone Sundan',
        'Yari',
        175,
        37,
        101,
        0,
        'high',
        'Necromancer',
        ((136, 0, 45), (252, 0, 10), (194, 0, 3), (17, 0, 180), (18, 0, 180)),
        (
            '45% Chance of Crushing Blow',
            'Repairs 1 durability in 10 seconds',
            '180% (160-200%) Enhanced Damage',
            'Sockets: 3 — 3 empty',
        ),
        side='merc',
    ),
    Review(
        'The Meat Scraper',
        'Lochaber Axe',
        177,
        41,
        80,
        0,
        'med',
        'Necromancer',
        ((93, 0, 30), (60, 0, 10), (135, 0, 50), (80, 0, 25), (188, 33, 3)),
        (
            '30% Increased Attack Speed',
            '10% Life stolen per hit',
            '50% Chance of Open Wounds',
            '25% Better Chance of Getting Magic Items',
            'Masteries (Barbarian Only)',
        ),
        side='merc',
    ),
    Review(
        'The Battlebranch',
        'Poleaxe',
        51,
        25,
        62,
        0,
        'med',
        'Necromancer',
        ((93, 0, 30), (60, 0, 7), (2, 0, 10), (17, 0, 60), (18, 0, 60), (19, 0, 75)),
        ('30% Increased Attack Speed', '7% Life stolen per hit', '60% (50-70%) Enhanced Damage'),
        side='merc',
    ),
)

CASES = tuple(
    replace(case, item=replace(case.item, sockets=3)) if case.item.name == 'Hone Sundan' else case
    for case in cases(REVIEWS, prefix='mercenary-progression-weapon')
)

HONE = next(case for case in CASES if case.id.endswith('Hone Sundan/equip-level'))
CASES += (
    replace(
        HONE,
        id='mercenary-progression-weapon/Hone Sundan/unknown-socket-contents',
        item=replace(HONE.item, socket_contents='unknown'),
        scenario='unknown',
        expected={
            'assessment': IsPartialDict(
                leveling=Contains(IsPartialDict(side='merc', requirements_fit=IsPartialDict(status='unknown')))
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=('Sockets: 3 — contents not captured',),
    ),
)

# Literal native-base costs after the ethereal reduction; owner attributes cannot
# satisfy these mercenary requirements. Empty native sockets add no equip cost.
for name, strength, dexterity in (
    ('Kelpie Snare', 67, 15),
    ('Hone Sundan', 91, 0),
    ('The Meat Scraper', 70, 0),
    ('The Battlebranch', 52, 0),
):
    original = next(case for case in CASES if case.id.endswith(f'{name}/equip-level'))
    for label, actual_strength, ethereal, fit, scenario in (
        ('ethereal-minimum', strength, True, 'met', 'positive'),
        ('ethereal-below-strength', strength - 1, True, 'unmet', 'negative'),
        ('unknown-ethereal', strength, None, 'unknown', 'unknown'),
    ):
        CASES += (
            replace(
                original,
                id=f'mercenary-progression-weapon/{name}/{label}',
                item=replace(original.item, ethereal=ethereal),
                context={**original.context, 'mercenary_strength': actual_strength, 'mercenary_dexterity': dexterity},
                scenario=scenario,
                expected={
                    'assessment': IsPartialDict(
                        leveling=Contains(
                            IsPartialDict(
                                side='merc',
                                requirements={
                                    'level': original.context['mercenary_level'],
                                    'strength': strength,
                                    'dexterity': dexterity,
                                }
                                if ethereal
                                else {},
                                requirements_fit=IsPartialDict(status=fit),
                            )
                        )
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=(),
            ),
        )
