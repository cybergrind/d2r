"""Authored premium boundaries from native rolls and the dated offline tier review.

These are partial captures: known rolls can justify a qualitative tier, but not a
numeric price for the entire item. Expectations do not read production predicates.
"""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REVIEWS = (
    (
        "Thundergod's Vigor",
        'War Belt',
        246,
        'UQ-thundergod-s-vigor',
        ((42, 0, 10), (145, 0, 20), (0, 0, 20), (3, 0, 20), (107, 34, 3), (107, 35, 3)),
        (
            ('perfect-defense', False, ((16, 0, 200),), 'low', 'positive', '(160-200%)'),
            ('lowest-defense', False, ((16, 0, 160),), 'low', 'negative', '(160-200%)'),
            ('unread-defense', False, (), 'low', 'unknown', 'Lightning Absorb'),
        ),
    ),
    (
        "Nightwing's Veil",
        'Spired Helm',
        343,
        'UQ-nightwing-s-veil',
        ((127, 0, 2),),
        (
            ('perfect-pair', False, ((331, 0, 15), (2, 0, 20)), 'high', 'positive', '(8-15%)'),
            ('perfect-cold-only', False, ((331, 0, 15), (2, 0, 10)), 'high', 'positive', '(8-15%)'),
            ('one-cold-short', False, ((331, 0, 14), (2, 0, 20)), 'low', 'negative', '(8-15%)'),
            ('unknown-cold', False, ((2, 0, 20),), 'low', 'unknown', '(10-20)'),
        ),
    ),
    (
        'Ravenlore',
        'Sky Spirit',
        350,
        'UQ-ravenlore',
        ((188, 41, 3), (1, 0, 25)),
        (
            ('perfect-pierce', False, ((333, 0, 20),), 'high', 'positive', '(10-20%)'),
            ('one-pierce-short', False, ((333, 0, 19),), 'low', 'negative', '(10-20%)'),
            ('unknown-pierce', False, (), 'low', 'unknown', '(20-30)'),
        ),
    ),
    (
        "Eschuta's Temper",
        'Eldritch Orb',
        367,
        'UQ-eschuta-s-temper',
        ((105, 0, 40),),
        (
            ('premium-lightning', False, ((83, 1, 3), (330, 0, 20)), 'high', 'positive', '(10-20%)'),
            ('one-lightning-short', False, ((83, 1, 3), (330, 0, 19)), 'low', 'negative', '(10-20%)'),
            ('one-skill-short', False, ((83, 1, 2), (330, 0, 20)), 'low', 'negative', '(1-3)'),
            ('unknown-lightning', False, ((83, 1, 3),), 'low', 'unknown', '(1-3)'),
        ),
    ),
    (
        "Verdungo's Hearty Cord",
        'Mithril Coil',
        376,
        'UQ-verdungo-s-hearty-cord',
        ((99, 0, 10),),
        (
            ('premium-boundary', False, ((3, 0, 38), (36, 0, 15)), 'high', 'positive', '(30-40)'),
            ('one-vitality-short', False, ((3, 0, 37), (36, 0, 15)), 'low', 'negative', '(30-40)'),
            ('one-reduction-short', False, ((3, 0, 40), (36, 0, 14)), 'low', 'negative', '(10-15%)'),
            ('unknown-reduction', False, ((3, 0, 40),), 'low', 'unknown', '(30-40)'),
        ),
    ),
    (
        "Andariel's Visage",
        'Demonhead',
        345,
        'UQ-andariel-s-visage',
        ((127, 0, 2), (93, 0, 20), (39, 0, -30), (45, 0, 70)),
        (
            ('eth-perfect', True, ((0, 0, 30), (60, 0, 10), (16, 0, 150)), 'high', 'positive', '(100-150%)'),
            ('noneth', False, ((0, 0, 30), (60, 0, 10), (16, 0, 150)), 'med', 'negative', '(100-150%)'),
            ('unknown-eth', None, ((0, 0, 30), (60, 0, 10)), 'med', 'unknown', '(8-10%)'),
        ),
    ),
    (
        'Arachnid Mesh',
        'Spiderweb Sash',
        373,
        'UQ-arachnid-mesh',
        ((105, 0, 20), (127, 0, 1), (77, 0, 5), (150, 0, 10)),
        (
            ('perfect', False, ((16, 0, 120),), 'high', 'positive', '(90-120%)'),
            ('former-high-boundary', False, ((16, 0, 110),), 'med', 'unknown', '(90-120%)'),
            ('below-reviewed-boundary', False, ((16, 0, 109),), 'med', 'negative', '(90-120%)'),
            ('one-ed-short-of-perfect', False, ((16, 0, 119),), 'med', 'unknown', '(90-120%)'),
            ('unknown-ed', False, (), 'med', 'unknown', 'Faster Cast Rate'),
        ),
    ),
    (
        'War Traveler',
        'Battle Boots',
        240,
        'UQ-war-traveler',
        ((96, 0, 25), (0, 0, 10), (3, 0, 10)),
        (
            ('perfect-mf', False, ((80, 0, 50),), 'high', 'positive', '(30-50%)'),
            ('one-mf-short', False, ((80, 0, 49),), 'med', 'negative', '(30-50%)'),
            ('unknown-mf', False, (), 'low', 'unknown', 'Faster Run/Walk'),
        ),
    ),
    (
        'Raven Frost',
        'Ring',
        275,
        'UQ-raven-frost',
        ((153, 0, 1), (9, 0, 40 << 8), (148, 0, 20)),
        (
            ('perfect-pair', False, ((2, 0, 20), (19, 0, 250)), 'high', 'positive', '(150-250)'),
            ('one-ar-short', False, ((2, 0, 20), (19, 0, 249)), 'med', 'negative', '(150-250)'),
            ('one-dex-short', False, ((2, 0, 19), (19, 0, 250)), 'med', 'negative', '(15-20)'),
            ('unknown-ar', False, ((2, 0, 20),), 'med', 'unknown', '(15-20)'),
        ),
    ),
)


def cases():
    for name, base, table_id, research, fixed, variants in REVIEWS:
        for label, ethereal, rolls, tier, scenario, report_stat in variants:
            yield Case(
                id=f'named-premium/{name}/{label}',
                item=Item(
                    base,
                    'unique',
                    name,
                    (*fixed, *rolls),
                    ethereal=ethereal,
                    owned_stats=tuple(row for row in rolls if row[0] == 16),
                ),
                context={},
                expected={
                    'assessment': IsPartialDict(
                        trade_tier=IsPartialDict(status='reviewed', tier=tier),
                        **(
                            {
                                'trade_qualification': IsPartialDict(
                                    status='premium'
                                    if label == 'perfect-pair'
                                    else 'unresolved'
                                    if label == 'unknown-ar'
                                    else 'candidate'
                                )
                            }
                            if name == 'Raven Frost'
                            else {}
                        ),
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                scenario=scenario,
                covers=('named:unique:' + name,),
                report_contains=(name, 'Trade tier: ' + ('mid' if tier == 'med' else tier), report_stat)
                + (
                    ('Trade: ' + ('premium' if label == 'perfect-pair' else 'ordinary') + ' candidate',)
                    if name == 'Raven Frost' and label != 'unknown-ar'
                    else ()
                ),
                report_absent=('Trade:',) if name == 'Raven Frost' and label == 'unknown-ar' else (),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                    'pricing/data/wp-i-uniques-misc.json:/' + research,
                ),
            )


CASES = tuple(cases())
