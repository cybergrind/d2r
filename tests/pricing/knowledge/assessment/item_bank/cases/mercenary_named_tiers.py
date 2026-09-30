"""Reviewed named premiums require the actual base, ethereal state and roll tuple.

Native tables and dated review evidence supply these explicit expectations.
The partial captures intentionally cannot establish numeric market estimates.
"""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Each row: case label, native base, ethereal flag, observed variable rolls,
# expected qualitative trade tier, scenario. Missing rolls remain unknown.
REVIEWS = (
    (
        'Guardian Angel',
        218,
        'player',
        '(180-200%)',
        ((102, 0, 30), (20, 0, 20)),
        (
            ('perfect-eth', 'Templar Coat', True, ((16, 0, 200),), 'high', 'positive'),
            ('one-ed-short', 'Templar Coat', True, ((16, 0, 199),), 'low', 'negative'),
            ('noneth', 'Templar Coat', False, ((16, 0, 200),), 'low', 'negative'),
            ('unknown-eth', 'Templar Coat', None, ((16, 0, 200),), 'low', 'unknown'),
        ),
    ),
    (
        'Shaftstop',
        215,
        'merc',
        '(180-220%)',
        ((36, 0, 30), (7, 0, 60 << 8), (32, 0, 250)),
        (
            ('upgraded-perfect-eth', 'Boneweave', True, ((16, 0, 220),), 'high', 'positive'),
            ('one-ed-short', 'Boneweave', True, ((16, 0, 219),), 'low', 'negative'),
            ('original-base', 'Mesh Armor', True, ((16, 0, 220),), 'low', 'negative'),
            ('noneth', 'Boneweave', False, ((16, 0, 220),), 'low', 'negative'),
            ('unknown-eth', 'Boneweave', None, ((16, 0, 220),), 'low', 'unknown'),
        ),
    ),
    (
        'Crown of Thieves',
        206,
        'merc',
        '(160-200%)',
        ((2, 0, 25), (7, 0, 50 << 8), (9, 0, 35 << 8), (39, 0, 33)),
        (
            ('original-band', 'Grand Crown', True, ((16, 0, 198), (79, 0, 100), (60, 0, 12)), 'high', 'positive'),
            ('original-below-band', 'Grand Crown', True, ((16, 0, 197), (79, 0, 100), (60, 0, 12)), 'low', 'negative'),
            ('low-leech', 'Grand Crown', True, ((16, 0, 200), (79, 0, 100), (60, 0, 11)), 'low', 'negative'),
            ('low-gold', 'Grand Crown', True, ((16, 0, 200), (79, 0, 99), (60, 0, 12)), 'low', 'negative'),
            ('upgraded-perfect', 'Corona', True, ((16, 0, 200), (79, 0, 100), (60, 0, 12)), 'high', 'positive'),
            ('upgraded-below-band', 'Corona', True, ((16, 0, 199), (79, 0, 100), (60, 0, 12)), 'low', 'negative'),
            ('unknown-eth', 'Grand Crown', None, ((16, 0, 200), (79, 0, 100), (60, 0, 12)), 'low', 'unknown'),
        ),
    ),
    (
        "Duriel's Shell",
        216,
        'merc',
        '(160-200%)',
        ((0, 0, 15), (153, 0, 1), (39, 0, 20), (41, 0, 20), (43, 0, 50), (45, 0, 20)),
        (
            ('reviewed-lower-bound', 'Cuirass', True, ((16, 0, 183),), 'med', 'positive'),
            ('reviewed-upper-bound', 'Cuirass', True, ((16, 0, 197),), 'med', 'positive'),
            ('below-reviewed-band', 'Cuirass', True, ((16, 0, 182),), 'low', 'negative'),
            ('above-reviewed-band', 'Cuirass', True, ((16, 0, 198),), 'med', 'positive'),
            ('legal-maximum', 'Cuirass', True, ((16, 0, 200),), 'med', 'positive'),
            ('beyond-native-range', 'Cuirass', True, ((16, 0, 201),), 'low', 'negative'),
            ('unknown-ed', 'Cuirass', True, (), 'low', 'unknown'),
            ('different-base', 'Great Hauberk', True, ((16, 0, 183),), 'low', 'negative'),
            ('unknown-eth', 'Cuirass', None, ((16, 0, 183),), 'low', 'unknown'),
        ),
    ),
    (
        'Stealskull',
        203,
        'merc',
        '(200-240%)',
        ((16, 0, 200), (60, 0, 5), (62, 0, 5), (99, 0, 10), (93, 0, 10)),
        (
            ('perfect-mf', 'Casque', False, ((80, 0, 50),), 'med', 'positive'),
            ('perfect-mf-eth', 'Casque', True, ((80, 0, 50),), 'med', 'positive'),
            ('one-mf-short', 'Casque', False, ((80, 0, 49),), 'low', 'negative'),
            ('unknown-mf', 'Casque', False, (), 'low', 'unknown'),
        ),
    ),
    (
        'Vampire Gaze',
        208,
        'merc',
        None,
        ((16, 0, 100), (62, 0, 6)),
        (
            ('premium-combination', 'Grim Helm', True, ((36, 0, 20), (60, 0, 8), (35, 0, 15)), 'high', 'positive'),
            ('noneth', 'Grim Helm', False, ((36, 0, 20), (60, 0, 8), (35, 0, 15)), 'med', 'negative'),
            ('low-dr', 'Grim Helm', True, ((36, 0, 19), (60, 0, 8), (35, 0, 15)), 'med', 'negative'),
            ('low-leech', 'Grim Helm', True, ((36, 0, 20), (60, 0, 7), (35, 0, 15)), 'med', 'negative'),
            ('low-mdr', 'Grim Helm', True, ((36, 0, 20), (60, 0, 8), (35, 0, 14)), 'med', 'negative'),
            ('unknown-dr', 'Grim Helm', True, ((60, 0, 8), (35, 0, 15)), 'med', 'unknown'),
            ('unknown-eth', 'Grim Helm', None, ((36, 0, 20), (60, 0, 8), (35, 0, 15)), 'med', 'unknown'),
        ),
    ),
)


def cases():
    for name, table_id, side, interval, fixed, variants in REVIEWS:
        for label, base, ethereal, rolls, tier, scenario in variants:
            raw = (*fixed, *rolls)
            yield Case(
                id=f'mercenary-named-tier/{name}/{label}',
                item=Item(
                    base, 'unique', name, raw, ethereal=ethereal, owned_stats=tuple(r for r in raw if r[0] == 16)
                ),
                context={},
                scenario=scenario,
                covers=(f'named:unique:{name}',),
                expected={
                    'assessment': IsPartialDict(
                        trade_tier=IsPartialDict(status='reviewed', tier=tier),
                        leveling=Contains(IsPartialDict(tier='med', side=side)),
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                report_contains=(name, f'Trade tier: {"mid" if tier == "med" else tier}')
                + ((interval,) if interval and any(r[0] == 16 for r in raw) and label != 'beyond-native-range' else ()),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                    'pricing/data/appraisal-named-tier-research.json',
                    'pricing/knowledge/assessment/rules/named_tier_reviews.json',
                    'pricing/knowledge/assessment/rules/named_leveling_reviews.json',
                ),
            )


CASES = tuple(cases())
