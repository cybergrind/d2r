"""Same native ID is not enough to borrow a seasonal stat or range on Non-Ladder."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BANE_SHARED = ((48, 0, 4), (49, 0, 6), (39, 0, 50), (9, 0, 30 * 256), (107, 36, 5), (107, 37, 2))
BANE = Item('Short Staff', 'unique', 'Bane Ash', (*BANE_SHARED, (17, 0, 55), (18, 0, 55), (93, 0, 20)), complete=True)
MANALD = Item('Ring', 'unique', 'Manald Heal', ((62, 0, 7), (74, 0, 8), (7, 0, 20 * 256), (27, 0, 20)), complete=True)


def cases():
    for name, item, table, ordinary_text, seasonal in (
        ('bane', BANE, 54, '(50-60%)', replace(BANE, raw_stats=(*BANE_SHARED, (105, 0, 20)))),
        ('manald', MANALD, 121, 'Manald Heal', replace(MANALD, raw_stats=(*MANALD.raw_stats, (105, 0, 10)))),
    ):
        for label, candidate, scenario in (
            ('ordinary', item, 'positive'),
            ('seasonal', seasonal, 'negative'),
            ('partial', replace(item, complete=False), 'unknown'),
        ):
            expected = {}
            if label in ('partial', 'seasonal'):
                expected = {
                    'price_estimate': IsPartialDict(estimate_ist=None),
                }
            if label == 'seasonal':
                expected['assessment'] = IsPartialDict(
                    contract=None, roles=[], leveling=[], trade_tier=IsPartialDict(status='out_of_scope')
                )
                expected['extraction'] = IsPartialDict(
                    source=IsPartialDict(item_identity=IsPartialDict(mode_eligibility='ladder_only'))
                )
            if name == 'bane' and label != 'seasonal':
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            name='item_damage_percent',
                            value=55,
                            roll_range=IsPartialDict(min=50, max=60),
                        )
                    )
                )
            contains = (candidate.name,)
            if label != 'seasonal':
                contains += (ordinary_text,)
            if label == 'seasonal':
                contains += ('Faster Cast Rate',)
            absent = ()
            if label != 'seasonal':
                absent += ('Faster Cast Rate',)
            if name == 'bane' and label == 'seasonal':
                absent += ('(50-60%)',)
            yield Case(
                id=f'seasonal-named-versions/{name}/{label}',
                item=candidate,
                context={},
                expected=expected,
                covers=('named:unique:' + item.name,),
                scenario=scenario,
                report_contains=contains,
                report_absent=absent,
                evidence=(
                    f'third-parties/d2data/json/base/uniqueitems.json:/{table}',
                    f'pricing/raw/d2data/uniqueitems.json:/{table}',
                ),
            )


CASES = tuple(cases())
