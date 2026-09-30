"""Named jewelry separates skill/leveling utility, rolled stats and resale tier."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case


REVIEWS = (
    Review(
        'The Stone of Jordan',
        'Ring',
        122,
        29,
        0,
        0,
        'high',
        'Paladin',
        ((127, 0, 1), (9, 0, 20 * 256), (77, 0, 25), (50, 0, 1), (51, 0, 12)),
        ('+1 to All Skills', '+20 to Mana', 'Increase Maximum Mana 25%', 'Adds 1-12 Lightning Damage'),
        trade='high',
    ),
    Review(
        "Bul-Kathos' Wedding Band",
        'Ring',
        268,
        58,
        0,
        0,
        'med',
        'Paladin',
        # Native life coefficients carry ValShift8 before the level divisor8.
        ((127, 0, 1), (216, 0, 4 * 256), (60, 0, 4)),
        ('+1 to All Skills', '+29 to Life (Based on Character Level)', '4% (3-5%) Life stolen per hit'),
        trade='med',
    ),
    Review(
        "Highlord's Wrath",
        'Amulet',
        276,
        65,
        0,
        0,
        'high',
        'Amazon',
        ((127, 0, 1), (93, 0, 20), (250, 0, 3), (41, 0, 35)),
        (
            '+1 to All Skills',
            '20% Increased Attack Speed',
            '24% Deadly Strike (Based on Character Level)',
            'Lightning Resist +35%',
        ),
        trade='med',
    ),
    Review(
        "The Cat's Eye",
        'Amulet',
        269,
        50,
        0,
        0,
        'high',
        'Amazon',
        ((96, 0, 30), (93, 0, 20), (2, 0, 25), (32, 0, 100)),
        ('30% Faster Run/Walk', '20% Increased Attack Speed', '+25 to Dexterity'),
    ),
    Review(
        'The Eye of Etlich',
        'Amulet',
        118,
        15,
        0,
        0,
        'high',
        'Paladin',
        ((127, 0, 1), (60, 0, 5), (54, 0, 2), (55, 0, 4), (56, 0, 100)),
        ('+1 to All Skills', '5% (3-7%) Life stolen per hit', 'Cold Damage'),
    ),
    Review(
        'The Mahim-Oak Curio',
        'Amulet',
        119,
        25,
        0,
        0,
        'med',
        'Paladin',
        ((0, 0, 10), (1, 0, 10), (2, 0, 10), (3, 0, 10), (119, 0, 10), (39, 0, 10)),
        ('+10 to Strength', '+10 to Dexterity', '10% Bonus to Attack Rating', 'Fire Resist +10%'),
    ),
    Review(
        'Dwarf Star',
        'Ring',
        274,
        45,
        0,
        0,
        'med',
        'Paladin',
        ((142, 0, 15), (35, 0, 13), (7, 0, 40 * 256), (79, 0, 100)),
        ('Fire Absorb +15%', 'Magic Damage Reduced by 13 (12-15)', '+40 to Life', '100% Extra Gold from Monsters'),
    ),
    Review(
        'Nagelring',
        'Ring',
        120,
        7,
        0,
        0,
        'low',
        'Paladin',
        ((80, 0, 21), (19, 0, 60), (35, 0, 3)),
        (
            '21% (15-30%) Better Chance of Getting Magic Items',
            '+60 (50-75) to Attack Rating',
            'Magic Damage Reduced by 3',
        ),
    ),
    Review(
        'Manald Heal',
        'Ring',
        121,
        15,
        0,
        0,
        'med',
        'Paladin',
        ((62, 0, 5), (27, 0, 20), (7, 0, 20 * 256)),
        ('5% (4-7%) Mana stolen per hit', 'Regenerate Mana 20%', '+20 to Life'),
    ),
)


CAPTURE_LEVELS = {"Bul-Kathos' Wedding Band": 58, "Highlord's Wrath": 65}
CASES = tuple(
    replace(case, item=replace(case.item, viewer_level=CAPTURE_LEVELS[case.item.name]))
    if case.item.name in CAPTURE_LEVELS
    else case
    for case in cases(REVIEWS, prefix='unique-jewelry-progression')
)


BK = next(case for case in CASES if case.id.endswith("Bul-Kathos' Wedding Band/equip-level"))
CASES += tuple(
    Case(
        id=f'bk-life-scaling/{level}',
        item=replace(BK.item, viewer_level=level),
        context=BK.context,
        scenario='unknown' if level is None else 'positive',
        covers=("named:unique:Bul-Kathos' Wedding Band",),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='med')),
            'price_estimate': IsPartialDict(estimate_ist=None),
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 216, 'layer': 0, 'raw': 1024},
                        value=value,
                        per_level={'numerator': 1024, 'denominator': 2048},
                    )
                )
            )
            if level is not None
            else IsPartialDict(unresolved_stats=Contains({'id': 216, 'layer': 0, 'raw': 1024})),
        },
        report_contains=(f'+{value} to Life (Based on Character Level)',) if level is not None else (),
        report_absent=('to Life (Based on Character Level)',) if level is None else (),
        evidence=(
            *BK.evidence,
            'third-parties/D2MOO/source/D2Common/src/Items/ItemMods.cpp:ITEMMODS_AddPropertyToItemStatList',
            'third-parties/d2data/json/itemstatcost.json:/item_hp_perlevel',
        ),
    )
    for level, value in ((59, 29), (99, 49), (None, None))
)
