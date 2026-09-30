"""Named progression gear: trade demand, equip boundaries and observed roll ranges.

Expectations are authored from native unique definitions and the dated leveling
reviews, not computed from the classifier. Partial captures cannot establish prices.
"""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# name, base, native ID, trade tier, leveling tier, level, strength,
# fixed observed modifiers, variable native stat, min/max and rendered range.
REVIEWED = (
    ('Tarnhelm', 'Skull Cap', 72, 'low', 'high', 15, 15, ((79, 0, 75), (127, 0, 1)), 80, 25, 50, '(25-50%)'),
    (
        'Chance Guards',
        'Chain Gloves',
        104,
        'low',
        'med',
        15,
        25,
        ((79, 0, 200), (19, 0, 25), (89, 0, 2)),
        80,
        25,
        40,
        '(25-40%)',
    ),
    (
        'Magefist',
        'Light Gauntlets',
        105,
        'low',
        'high',
        23,
        45,
        ((105, 0, 20), (27, 0, 25), (126, 1, 1), (48, 0, 1), (49, 0, 6)),
        16,
        20,
        30,
        '(20-30%)',
    ),
    (
        'Frostburn',
        'Gauntlets',
        106,
        'low',
        'med',
        29,
        60,
        ((77, 0, 40), (17, 0, 5), (18, 0, 5), (54, 0, 1), (55, 0, 6), (56, 0, 50)),
        16,
        10,
        20,
        '(10-20%)',
    ),
    (
        'Goldwrap',
        'Heavy Belt',
        115,
        'trash',
        'med',
        27,
        45,
        ((80, 0, 30), (93, 0, 10), (89, 0, 2)),
        79,
        50,
        80,
        '(50-80%)',
    ),
    (
        'Peasant Crown',
        'War Hat',
        201,
        'trash',
        'med',
        28,
        20,
        ((1, 0, 20), (3, 0, 20), (127, 0, 1), (96, 0, 15)),
        74,
        6,
        12,
        '(6-12)',
    ),
    (
        'Skin of the Vipermagi',
        'Serpentskin Armor',
        210,
        'low',
        'high',
        29,
        43,
        ((105, 0, 30), (35, 0, 9), (127, 0, 1)),
        39,
        20,
        35,
        '(20-35%)',
    ),
    (
        'Lidless Wall',
        'Grim Shield',
        230,
        'low',
        'med',
        41,
        58,
        ((89, 0, 1), (127, 0, 1), (105, 0, 20), (1, 0, 10), (77, 0, 10)),
        138,
        3,
        5,
        '(3-5)',
    ),
)


def cases():
    result = []
    for name, base, native_id, trade, leveling, level, strength, fixed, stat, low, high, interval in REVIEWED:
        scenarios = [('positive', high, 'met'), ('negative', low, 'unmet'), ('unknown', None, 'unknown')]
        if name in ('Chance Guards', 'Skin of the Vipermagi'):
            scenarios.append(('near-premium', high - 1, 'met'))
        for scenario, value, fit in scenarios:
            assessed_trade = trade
            if name == 'Chance Guards' and value == 40:
                assessed_trade = 'med'
            if name == 'Skin of the Vipermagi' and value is not None:
                assessed_trade = 'high' if value == 35 else 'med' if value >= 30 else 'low'
            context = {'player_class': 'Sorceress', 'player_strength': strength, 'player_dexterity': 0}
            if scenario != 'unknown':
                context['player_level'] = level - 1 if scenario == 'negative' else level
            variable = () if value is None else ((stat, 0, value),)
            if name == 'Skin of the Vipermagi' and value is not None:
                variable = tuple((key, 0, value) for key in (39, 41, 43, 45))
            result.append(
                Case(
                    id=f'leveling-unique/{name}/{scenario}',
                    item=Item(base, 'unique', name, (*fixed, *variable), owned_stats=variable if stat == 16 else None),
                    context=context,
                    scenario='negative' if scenario == 'near-premium' else scenario,
                    covers=(f'named:unique:{name}',),
                    expected={
                        'assessment': IsPartialDict(
                            trade_tier=IsPartialDict(status='reviewed', tier=assessed_trade),
                            leveling=Contains(
                                IsPartialDict(
                                    tier=leveling,
                                    required_level=level,
                                    requirements_fit=IsPartialDict(status=fit),
                                )
                            ),
                        ),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    report_contains=(
                        name,
                        f'Trade tier: {"mid" if assessed_trade == "med" else assessed_trade}',
                        *(('Leveling: high',) if leveling == 'high' else ()),
                    )
                    + ((interval,) if value is not None else ()),
                    report_absent=('Leveling: mid', 'Leveling: low'),
                    evidence=(
                        f'third-parties/d2data/json/uniqueitems.json:/{native_id}',
                        'pricing/knowledge/assessment/rules/named_tier_reviews.json',
                        f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:unique:{name}',
                        'pricing/data/appraisal-recommendations.json',
                        'pricing/data/wp-i-uniques-misc.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
