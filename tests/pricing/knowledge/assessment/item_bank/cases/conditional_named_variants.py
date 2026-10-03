"""Independent named specimens whose valuable variants exceed their low baselines."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


DEATH = Item(
    'Berserker Axe',
    'unique',
    'Death Cleaver',
    ((17, 0, 260), (18, 0, 260), (141, 0, 66), (116, 0, 33), (93, 0, 40), (86, 0, 8)),
    ethereal=True,
    named_table_id=314,
    complete=True,
)
ARCH = Item(
    'Balrog Spear',
    'unique',
    "Demon's Arch",
    (
        (17, 0, 180),
        (18, 0, 180),
        (48, 0, 232),
        (49, 0, 323),
        (60, 0, 9),
        (253, 0, 30),
        (93, 0, 30),
        (50, 0, 23),
        (51, 0, 333),
    ),
    ethereal=True,
    named_table_id=340,
    complete=True,
)
TOMB = Item(
    'Cryptic Axe',
    'unique',
    'Tomb Reaver',
    (
        (93, 0, 60),
        (89, 0, 4),
        (17, 0, 240),
        (18, 0, 240),
        (122, 0, 190),
        (80, 0, 65),
        *((stat, 0, 40) for stat in (39, 41, 43, 45)),
        (124, 0, 300),
        (155, 1, 10),
        (86, 0, 12),
        (194, 0, 3),
    ),
    ethereal=True,
    sockets=3,
    named_table_id=298,
    complete=True,
)
KIRA = Item(
    'Tiara',
    'unique',
    "Kira's Guardian",
    ((31, 0, 100), (99, 0, 20), (153, 0, 1), *((stat, 0, 70) for stat in (39, 41, 43, 45))),
    named_table_id=357,
    complete=True,
)


def cases():
    specimens = []
    for item, tier in ((DEATH, 'high'), (ARCH, 'med'), (TOMB, 'med')):
        specimens.extend(
            (
                ('ethereal', item, 'positive', tier),
                ('nonethereal', replace(item, ethereal=False), 'negative', 'low'),
                ('unknown-ethereal', replace(item, ethereal=None), 'unknown', 'low'),
            )
        )
    perfect = {17: 280, 18: 280, 122: 230, 80: 80, 39: 50, 41: 50, 43: 50, 45: 50, 124: 350, 86: 14}
    specimens.extend(
        (
            (
                'perfect-three-socket',
                replace(TOMB, raw_stats=tuple((s, p, perfect.get(s, v)) for s, p, v in TOMB.raw_stats)),
                'positive',
                'high',
            ),
            (
                'two-socket',
                replace(TOMB, sockets=2, raw_stats=tuple((s, p, 2 if s == 194 else v) for s, p, v in TOMB.raw_stats)),
                'negative',
                'low',
            ),
            ('perfect-resistance', KIRA, 'positive', 'med'),
            (
                'one-resistance-short',
                replace(
                    KIRA, raw_stats=tuple((s, p, 69 if s in (39, 41, 43, 45) else v) for s, p, v in KIRA.raw_stats)
                ),
                'negative',
                'low',
            ),
            (
                'missing-resistance',
                replace(KIRA, complete=False, raw_stats=tuple(row for row in KIRA.raw_stats if row[0] != 39)),
                'unknown',
                'low',
            ),
        )
    )
    for label, item, scenario, tier in specimens:
        yield Case(
            id=f'conditional-named/{item.name}/{label}',
            item=item,
            context={},
            scenario=scenario,
            covers=(f'named:unique:{item.name}',),
            expected={
                'assessment': IsPartialDict(
                    trade_tier=IsPartialDict(
                        tier=tier,
                        variant=IsPartialDict(tier=None if scenario == 'unknown' else tier),
                    )
                )
            },
            report_contains=(item.name, f'Trade tier: {"mid" if tier == "med" else tier}'),
            evidence=(
                f'third-parties/d2data/json/uniqueitems.json:/{item.named_table_id}',
                f'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:{item.name}',
            ),
        )


CASES = tuple(cases())
