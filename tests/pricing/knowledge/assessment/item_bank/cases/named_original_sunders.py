"""Original sunder penalty quality and exact native effect, independent of build class."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('Cold Rupture', 401, 187, 43, -90, -70),
    ('Flame Rift', 402, 189, 39, -90, -70),
    ('Crack of the Heavens', 403, 190, 41, -90, -70),
    ('Bone Break', 405, 192, 36, -20, -10),
    ('Black Cleft', 406, 193, 37, -65, -45),
)


def cases():
    for name, table_id, effect, penalty, worst, best in SPECS:
        for label, roll, native_effect, scenario in (
            ('best-penalty', best, 300, 'positive'),
            ('worst-penalty', worst, 300, 'negative'),
            ('unread-penalty', None, 300, 'unknown'),
            ('invalid-native-effect', best, 299, 'negative'),
        ):
            valid = roll is not None and native_effect == 300
            stats = ((effect, 0, native_effect),) + (((penalty, 0, roll),) if roll is not None else ())
            # The observed penalty is independent of trade tier: a perfect original
            # charm does not inherit a Ladder-start or renewed-version premium.
            expected = {
                'assessment': IsPartialDict(
                    trade_tier=IsPartialDict(tier='low'),
                    contract=IsPartialDict(name=name, family='charm', mode='exact_variant') if valid else None,
                )
            }
            if roll is not None:
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat={'id': penalty, 'layer': 0, 'raw': roll},
                            roll_quality='perfect' if roll == best else 'low',
                        )
                    )
                )
            if not valid:
                expected['price_estimate'] = IsPartialDict(estimate_ist=None)
            yield Case(
                id=f'named-original-sunder/{name}/{label}',
                item=Item('Grand Charm', 'unique', name, stats, complete=roll is not None, named_table_id=table_id),
                context={},
                expected=expected,
                covers=('named:unique:' + name,),
                scenario=scenario,
                report_contains=(name, 'Trade tier: low'),
                report_absent=('Trade tier: high',),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                    f'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:{name}',
                ),
            )


CASES = tuple(cases())
