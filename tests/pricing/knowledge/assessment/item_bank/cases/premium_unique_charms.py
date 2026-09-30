"""Native charm roll boundaries from September 18 research, not policy-generated items."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CHARMS = (
    ('Annihilus', 'Small Charm', 381, 'CH-anni-19plus', ((127, 0, 1), (85, 0, 10)), 19),
    (
        'Hellfire Torch',
        'Large Charm',
        400,
        'CH-torch-sorceress-18plus',
        ((83, 1, 3), (89, 0, 8), (198, 197 * 64 + 10, 5), (204, 62 * 64 + 30, 10 * 256 + 10)),
        18,
    ),
)


def cases():
    for name, base, table_id, research, fixed, threshold in CHARMS:
        for label, attributes, resists, tier, scenario in (
            ('perfect', 20, 20, 'high', 'positive'),
            ('premium-boundary', threshold, threshold, 'high', 'positive'),
            ('attributes-below', threshold - 1, threshold, 'low', 'negative'),
            ('resists-below', threshold, threshold - 1, 'low', 'negative'),
            ('unread-attributes', None, threshold, 'low', 'unknown'),
            ('unread-resists', threshold, None, 'low', 'unknown'),
        ):
            rolls = tuple(
                (stat, 0, value)
                for stats, value in (
                    ((0, 1, 2, 3), attributes),
                    ((39, 41, 43, 45), resists),
                )
                if value is not None
                for stat in stats
            )
            yield Case(
                id=f'premium-unique-charm/{name}/{label}',
                item=Item(
                    base,
                    'unique',
                    name,
                    (*fixed, *rolls),
                    named_table_id=table_id,
                    complete=attributes is not None and resists is not None,
                ),
                context={},
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=('named:unique:' + name,),
                scenario=scenario,
                report_contains=(name, 'Trade tier: ' + tier, '(10-20%)' if attributes is None else '(10-20)'),
                report_absent=('Trade tier: high',) if tier == 'low' else (),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                    f'pricing/data/wp-h-jewels-charms.json:/{research}',
                ),
            )


CASES = tuple(cases())


def class_cases():
    # WP-H distinguishes premium Sorceress rolls from ordinary Barbarian rolls;
    # perfect Barbarian 20/20 remains valuable. Missing class is not Sorceress.
    for label, skill_layer, roll, tier, scenario in (
        ('barbarian-18', 4, 18, 'low', 'negative'),
        ('barbarian-perfect', 4, 20, 'high', 'positive'),
        ('unread-class', None, 20, 'low', 'unknown'),
    ):
        stats = tuple((stat, 0, roll) for stat in (0, 1, 2, 3, 39, 41, 43, 45))
        fixed = CHARMS[1][4][1:]
        skill = () if skill_layer is None else ((83, skill_layer, 3),)
        yield Case(
            id=f'premium-unique-charm/Hellfire Torch/{label}',
            item=Item(
                'Large Charm',
                'unique',
                'Hellfire Torch',
                (*skill, *fixed, *stats),
                complete=skill_layer is not None,
                named_table_id=400,
            ),
            context={},
            expected={
                'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
            covers=('named:unique:Hellfire Torch',),
            scenario=scenario,
            report_contains=('Hellfire Torch', 'Trade tier: ' + tier, '(10-20)'),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/400',
                'pricing/data/wp-h-jewels-charms.json:/CH-torch-sorceress-18plus',
            ),
        )


CASES += tuple(class_cases())
