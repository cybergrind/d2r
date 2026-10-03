"""Magic-find use distinguishes fixed bonuses, wearer-level scaling and rolled premiums."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWS = (
    Review(
        'Gull',
        'Dagger',
        39,
        4,
        0,
        0,
        'med',
        'Sorceress',
        ((80, 0, 100), (9, 0, -5 * 256)),
        ('100% Better Chance of Getting Magic Items', '-5 to Mana'),
    ),
    Review(
        'Blade of Ali Baba',
        'Tulwar',
        157,
        35,
        70,
        42,
        'med',
        'Sorceress',
        ((194, 0, 2), (239, 0, 20), (240, 0, 8), (9, 0, 15 * 256), (2, 0, 10)),
        (
            '87% Extra Gold from Monsters (Based on Character Level)',
            '35% Better Chance of Getting Magic Items (Based on Character Level)',
            'Sockets: 2 — 2 empty',
        ),
    ),
    Review(
        "Skullder's Ire",
        'Russet Armor',
        217,
        42,
        97,
        0,
        'med',
        'Sorceress',
        ((127, 0, 1), (240, 0, 10), (16, 0, 180), (252, 0, 20), (35, 0, 10)),
        (
            '+1 to All Skills',
            '52% Better Chance of Getting Magic Items (Based on Character Level)',
            'Repairs 1 durability in 5 seconds',
            '180% (160-200%) Enhanced Defense',
        ),
        trade='med',
    ),
)

CASES = tuple(
    replace(case, item=replace(case.item, sockets=2, viewer_level=35))
    if case.item.name == 'Blade of Ali Baba'
    else replace(case, item=replace(case.item, viewer_level=42))
    if case.item.name == "Skullder's Ire"
    else case
    for case in cases(REVIEWS, prefix='magic-find-unique')
)


def gheed_cases():
    for magic_find, tier, quality, scenario in (
        (20, 'med', 'low', 'negative'),
        (37, 'med', 'normal', 'negative'),
        # The reviewed asking segment requires 40 MF; 38 is not a premium.
        (38, 'med', 'normal', 'negative'),
        (40, 'high', 'perfect', 'positive'),
        (None, 'med', None, 'unknown'),
    ):
        stats = ((79, 0, 120), (87, 0, 12)) + (((80, 0, magic_find),) if magic_find is not None else ())
        yield Case(
            id=f'magic-find-unique/Gheed/{magic_find}',
            item=Item('Grand Charm', 'unique', "Gheed's Fortune", stats),
            context={},
            scenario=scenario,
            covers=("named:unique:Gheed's Fortune",),
            expected={
                'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier), leveling=[]),
                'price_estimate': IsPartialDict(estimate_ist=None),
                **(
                    {
                        'extraction': IsPartialDict(
                            decoded_stats=Contains(
                                IsPartialDict(
                                    memory_stat={'id': 80, 'layer': 0, 'raw': magic_find},
                                    roll_range=IsPartialDict(min=20, max=40),
                                    roll_quality=quality,
                                )
                            )
                        )
                    }
                    if magic_find is not None
                    else {}
                ),
            },
            report_contains=(f'Trade tier: {"mid" if tier == "med" else tier}',),
            report_absent=('Leveling:',),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/359',
                'pricing/knowledge/assessment/rules/named_tiers.json',
                'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                'pricing/data/wp-i-uniques-misc.json:/UQ-gheed-s-fortune',
            ),
        )


CASES += tuple(gheed_cases())

for name, level, value in (("Skullder's Ire", 99, 123), ('Blade of Ali Baba', 99, 99)):
    original = next(case for case in CASES if case.id.endswith(f'{name}/equip-level'))
    CASES += (
        replace(
            original,
            id=f'magic-find-unique/{name}/viewer99',
            item=replace(original.item, viewer_level=level),
            report_contains=(f'{value}% Better Chance of Getting Magic Items (Based on Character Level)',),
        ),
        replace(
            original,
            id=f'magic-find-unique/{name}/viewer-unknown',
            item=replace(original.item, viewer_level=None),
            scenario='unknown',
            report_contains=(),
            expected={
                'price_estimate': IsPartialDict(estimate_ist=None),
                'extraction': IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat={'id': 240, 'layer': 0, 'raw': 10 if name == "Skullder's Ire" else 8},
                            status='unresolved',
                        )
                    )
                ),
            },
            report_absent=('Better Chance of Getting Magic Items (Based on Character Level)',),
        ),
    )
