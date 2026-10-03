"""Late weapons retain named tiers while exposing procs, auras and native damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


REVIEWS = (
    (
        "The Reaper's Toll",
        'Thresher',
        326,
        ((17, 0, 215), (18, 0, 215), (198, 87 * 64 + 1, 33), (60, 0, 13), (141, 0, 33), (91, 0, -25)),
        198,
        (
            '33% Chance to cast level 1 Decrepify on striking',
            '13% (11-15%) Life stolen per hit',
            '215% (190-240%) Enhanced Damage',
        ),
    ),
    (
        'Windforce',
        'Hydra Bow',
        266,
        ((218, 0, 25), (62, 0, 7), (81, 0, 1), (93, 0, 20), (17, 0, 250), (18, 0, 250)),
        62,
        ('+309 to Maximum Damage (Based on Character Level)', '7% (6-8%) Mana stolen per hit', 'Knockback'),
    ),
    (
        'Stormlash',
        'Scourge',
        360,
        (
            (17, 0, 270),
            (18, 0, 270),
            (198, 42 * 64 + 10, 15),
            (198, 245 * 64 + 18, 20),
            (50, 0, 1),
            (51, 0, 473),
            (136, 0, 33),
        ),
        136,
        (
            '15% Chance to cast level 10 Static Field on striking',
            '20% Chance to cast level 18 Tornado on striking',
            'Adds 1-473 Lightning Damage',
        ),
    ),
    (
        'Azurewrath',
        'Phase Blade',
        301,
        (
            (52, 0, 250),
            (53, 0, 500),
            (54, 0, 250),
            (55, 0, 500),
            (56, 0, 250),
            (151, 119, 11),
            (127, 0, 1),
            (17, 0, 250),
            (18, 0, 250),
        ),
        151,
        ('Adds 250-500 Magic Damage', 'Adds 250-500 Cold Damage', 'Sanctuary Aura When Equipped'),
    ),
    (
        'Lacerator',
        'Winged Axe',
        321,
        ((17, 0, 180), (18, 0, 180), (198, 66 * 64 + 3, 33), (112, 0, 64), (135, 0, 33)),
        198,
        ('33% Chance to cast level 3 Amplify Damage on striking', 'Hit Causes Monster to Flee +50%'),
    ),
    (
        'Warshrike',
        'Winged Knife',
        292,
        ((17, 0, 225), (18, 0, 225), (156, 0, 50), (141, 0, 50), (198, 48 * 64 + 9, 25)),
        198,
        ('50% Piercing Attack', '50% Deadly Strike', '25% Chance to cast level 9 Nova on striking'),
    ),
)


def cases():
    for name, base, native, stats, missing, snippets in REVIEWS:
        item = Item(base, 'unique', name, stats, viewer_level=99, named_table_id=native)
        for label, candidate, scenario, tier in (
            ('observed', item, 'positive', 'med'),
            ('unknown-stat', replace(item, raw_stats=tuple(s for s in stats if s[0] != missing)), 'unknown', 'med'),
            ('unidentified', replace(item, identified=False), 'negative', None),
        ):
            yield Case(
                id=f'late-unique-weapon/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier), leveling=[]),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=snippets if label == 'observed' else (),
                report_absent=('Leveling:',) if tier else ('Trade tier:', 'Leveling:'),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    'pricing/knowledge/assessment/rules/named_tiers.json',
                    'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                    'third-parties/d2data/json/skills.json',
                ),
            )


CASES = tuple(cases())
for name, tier in (("The Reaper's Toll", 'med'), ('Lacerator', 'high'), ('Warshrike', 'high')):
    original = next(case for case in CASES if case.id == f'late-unique-weapon/{name}/observed')
    CASES += (
        replace(
            original,
            id=f'late-unique-weapon/{name}/ethereal',
            item=replace(original.item, ethereal=True),
            expected={
                'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier), leveling=[]),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
        ),
    )

WIND = next(case for case in CASES if case.id == 'late-unique-weapon/Windforce/observed')
CASES += (
    replace(
        WIND,
        id='late-unique-weapon/Windforce/perfect-leech',
        item=replace(WIND.item, raw_stats=(*tuple(s for s in WIND.item.raw_stats if s[0] != 62), (62, 0, 8))),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='high')),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=('8% (6-8%) Mana stolen per hit', 'Trade tier: high'),
    ),
)
AZURE = next(case for case in CASES if case.id == 'late-unique-weapon/Azurewrath/observed')
CASES += tuple(
    replace(
        AZURE,
        id=f'late-unique-weapon/Azurewrath/aura-{rank}',
        item=replace(AZURE.item, raw_stats=(*tuple(s for s in AZURE.item.raw_stats if s[0] != 151), (151, 119, rank))),
        expected={
            'extraction': IsPartialDict(
                decoded_stats=Contains(
                    IsPartialDict(
                        memory_stat={'id': 151, 'layer': 119, 'raw': rank},
                        roll_range=IsPartialDict(min=10, max=13),
                        roll_quality=quality,
                    )
                )
            ),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
    )
    for rank, quality in ((10, 'low'), (13, 'perfect'))
)


# Native Windforce mana steal is 6-8; total includes the declared weapon insert.
for insert, mana, life in (('Vex Rune', 7, 0), ('Perfect Skull', 3, 4)):
    for native in (5, 6, 7, 8, 9):
        raw = tuple((s, p, native + mana if s == 62 else v) for s, p, v in WIND.item.raw_stats)
        raw += ((0, 0, 10), (2, 0, 5), (28, 0, 30), (194, 0, 1))
        if life:
            raw += ((60, 0, life),)
        valid = 6 <= native <= 8
        CASES += (
            replace(
                WIND,
                id=f'windforce-leech-socket/{insert}/{native}',
                item=replace(
                    WIND.item,
                    raw_stats=raw,
                    complete=True,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem(insert),),
                ),
                expected={
                    'assessment': IsPartialDict(
                        contract=IsPartialDict(
                            properties=IsPartialDict({'463': native + mana}), socket_payload=[insert]
                        )
                        if valid
                        else None
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=('Sockets: 1', 'Vex' if insert == 'Vex Rune' else 'Perfect Skull'),
                report_absent=('Price: ~',),
                evidence=(*WIND.evidence, 'third-parties/d2data/json/gems.json'),
            ),
        )
