"""Caster roll boundaries, item-granted charges and late-game utility identities."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ONDAL = Review(
    "Ondal's Wisdom",
    'Elder Staff',
    388,
    66,
    44,
    37,
    'med',
    'Sorceress',
    ((105, 0, 45), (1, 0, 45), (127, 0, 3), (85, 0, 5), (35, 0, 6)),
    ('45% Faster Cast Rate', '+3 (2-4) to All Skills', '5% to Experience Gained'),
    trade='med',
)
CASES = tuple(cases((ONDAL,), prefix='caster-utility-unique'))

REVIEWS = (
    (
        "Death's Fathom",
        'Dimensional Shard',
        354,
        'high',
        ((83, 1, 3), (331, 0, 25), (105, 0, 20), (39, 0, 35), (41, 0, 35)),
        331,
        ('+3 to Sorceress Skill Levels', '20% Faster Cast Rate', 'Cold Skill Damage'),
    ),
    (
        "Ormus' Robes",
        'Dusk Shroud',
        358,
        'med',
        ((105, 0, 20), (329, 0, 12), (330, 0, 12), (331, 0, 15), (107, 59, 3)),
        107,
        ('+3 to Blizzard (Sorceress Only)', '20% Faster Cast Rate', '(10-15%)'),
    ),
    (
        'Metalgrid',
        'Amulet',
        375,
        'med',
        (
            (31, 0, 325),
            (19, 0, 425),
            (39, 0, 30),
            (41, 0, 30),
            (43, 0, 30),
            (45, 0, 30),
            (204, 90 * 64 + 22, 11 * 256 + 9),
            (204, 76 * 64 + 12, 20 * 256 + 18),
        ),
        19,
        ('Level 22 Iron Golem (9/11 Charges)', 'Level 12 Iron Maiden (18/20 Charges)', 'Fire Resist +30% (25-35%)'),
    ),
    (
        'Wisp Projector',
        'Ring',
        319,
        'high',
        (
            (144, 0, 20),
            (80, 0, 20),
            (198, 49 * 64 + 16, 10),
            (204, 226 * 64 + 2, 15 * 256 + 12),
            (204, 236 * 64 + 5, 13 * 256 + 11),
            (204, 246 * 64 + 7, 11 * 256 + 10),
        ),
        144,
        (
            '10% Chance to cast level 16 Lightning on striking',
            'Level 2 Oak Sage (12/15 Charges)',
            'Level 5 Heart of Wolverine (11/13 Charges)',
            'Level 7 Spirit of Barbs (10/11 Charges)',
        ),
    ),
    (
        "Tyrael's Might",
        'Sacred Armor',
        311,
        'high',
        ((91, 0, -100), (152, 0, 1), (16, 0, 135), (108, 0, 1), (153, 0, 1), (96, 0, 20)),
        16,
        ('Requirements -100%', 'Indestructible', 'Slain Monsters Rest in Peace', 'Cannot Be Frozen'),
    ),
)


def late_cases():
    for name, base, native, tier, stats, missing, snippets in REVIEWS:
        item = Item(base, 'unique', name, stats, named_table_id=native)
        for label, candidate, expected_tier, scenario in (
            ('observed', item, tier, 'positive'),
            (
                'missing-stat',
                replace(item, raw_stats=tuple(s for s in stats if s[0] != missing)),
                'high' if name == "Tyrael's Might" else 'med',
                'unknown',
            ),
            ('unidentified', replace(item, identified=False), None, 'negative'),
        ):
            yield Case(
                id=f'caster-utility-unique/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=expected_tier), leveling=[]),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=snippets if label == 'observed' else (),
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Leveling:',) if expected_tier else ('Leveling:', 'Trade tier:')),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'third-parties/d2data/json/skills.json',
                    'pricing/knowledge/assessment/rules/named_tiers.json',
                    'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                ),
            )


CASES += tuple(late_cases())
FATHOM = next(case for case in CASES if case.id == "caster-utility-unique/Death's Fathom/observed")
CASES += tuple(
    replace(
        FATHOM,
        id=f'caster-utility-unique/Fathom/cold-{value}',
        item=replace(FATHOM.item, raw_stats=(*tuple(s for s in FATHOM.item.raw_stats if s[0] != 331), (331, 0, value))),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 331, 'layer': 0, 'raw': value},
                        roll_range=IsPartialDict(min=15, max=30),
                        roll_quality=quality,
                    )
                )
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
    )
    for value, tier, quality in ((15, 'med', 'low'), (24, 'med', 'normal'), (30, 'high', 'perfect'))
)

WISP = next(case for case in CASES if case.id == 'caster-utility-unique/Wisp Projector/observed')
CASES += tuple(
    replace(
        WISP,
        id=f'caster-utility-unique/Wisp/near-perfect-{stat}',
        item=replace(WISP.item, raw_stats=(*(s for s in WISP.item.raw_stats if s[0] != stat), (stat, 0, 19))),
        scenario='negative',
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='med'), leveling=[]),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=('Trade tier: mid',),
    )
    for stat in (80, 144)
)
CASES += (
    replace(
        WISP,
        id='caster-utility-unique/Wisp/depleted-oak-charges',
        item=replace(
            WISP.item,
            raw_stats=tuple(
                (stat, layer, 15 * 256 if (stat, layer) == (204, 226 * 64 + 2) else raw)
                for stat, layer, raw in WISP.item.raw_stats
            ),
        ),
        report_contains=('Level 2 Oak Sage (0/15 Charges)', 'Trade tier: high'),
    ),
)
ONDAL_CASE = next(case for case in CASES if case.id.endswith("Ondal's Wisdom/equip-level"))
CASES += tuple(
    replace(
        ONDAL_CASE,
        id=f'caster-utility-unique/Ondal/skills-{rank}',
        item=replace(
            ONDAL_CASE.item, raw_stats=(*(s for s in ONDAL_CASE.item.raw_stats if s[0] != 127), (127, 0, rank))
        ),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='med')),
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 127, 'layer': 0, 'raw': rank},
                        roll_range=IsPartialDict(min=2, max=4),
                        roll_quality=quality,
                    )
                )
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=(f'+{rank} (2-4) to All Skills', 'Trade tier: mid'),
        report_absent=('Leveling: mid', 'Leveling: low'),
    )
    for rank, quality in ((2, 'low'), (4, 'perfect'))
)
