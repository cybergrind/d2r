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


# Native ordinary unique records 12, 59, 80 and 154. Values below are chosen
# independently from their compiler output; resource totals use 8-bit fixed point.
ADDITIONAL_ITEMS = (
    (
        12,
        Item(
            'Bone Wand',
            'unique',
            'Gravenspine',
            (
                (0, 0, 10),
                (2, 0, 10),
                (54, 0, 4),
                (55, 0, 8),
                (56, 0, 75),
                (62, 0, 5),
                (83, 2, 2),
                (9, 0, 40 * 256),
            ),
            complete=True,
        ),
        105,
        None,
        10,
        'Faster Cast Rate',
    ),
    (
        59,
        Item(
            'Short Bow',
            'unique',
            'Pluckeye',
            (
                (19, 0, 28),
                (17, 0, 100),
                (18, 0, 100),
                (7, 0, 10 * 256),
                (89, 0, 2),
                (62, 0, 3),
                (138, 0, 2),
            ),
            complete=True,
        ),
        93,
        None,
        25,
        'Increased Attack Speed',
    ),
    (
        80,
        Item(
            'Leather Armor',
            'unique',
            "Blinkbat's Form",
            (
                (32, 0, 50),
                (96, 0, 10),
                (31, 0, 40),
                (48, 0, 3),
                (49, 0, 6),
                (99, 0, 40),
            ),
            complete=True,
        ),
        96,
        10,
        30,
        'Faster Run/Walk',
    ),
    (
        154,
        Item(
            'Gladius',
            'unique',
            'Bloodletter',
            (
                (21, 0, 12),
                (22, 0, 45),
                (19, 0, 90),
                (60, 0, 8),
                (154, 0, 10),
                (93, 0, 20),
                (17, 0, 140),
                (18, 0, 140),
                (107, 127, 3),
                (107, 151, 2),
                (72, 0, 54),
                (73, 0, 54),
            ),
            complete=True,
        ),
        96,
        None,
        20,
        'Faster Run/Walk',
    ),
)


def additional_cases():
    for table, ordinary, stat, old_value, new_value, label in ADDITIONAL_ITEMS:
        raw = tuple(s for s in ordinary.raw_stats if s[0] != stat)
        seasonal = replace(ordinary, raw_stats=(*raw, (stat, 0, new_value)))
        if table == 80:
            seasonal = replace(seasonal, raw_stats=(*seasonal.raw_stats, (138, 0, 1)))
        for variant, item, scenario in (
            ('ordinary', ordinary, 'positive'),
            ('seasonal', seasonal, 'negative'),
            ('partial', replace(ordinary, complete=False), 'unknown'),
        ):
            expected = {}
            if variant == 'seasonal':
                expected = {
                    'assessment': IsPartialDict(
                        contract=None, roles=[], leveling=[], trade_tier=IsPartialDict(status='out_of_scope')
                    ),
                    'extraction': IsPartialDict(
                        source=IsPartialDict(item_identity=IsPartialDict(mode_eligibility='ladder_only'))
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                }
            elif variant == 'partial':
                expected = {'price_estimate': IsPartialDict(estimate_ist=None)}
            yield Case(
                id=f'seasonal-named-versions/{table}/{variant}',
                item=item,
                context={},
                expected=expected,
                covers=('named:unique:' + ordinary.name,),
                scenario=scenario,
                report_contains=(ordinary.name,)
                + ((label,) if variant == 'seasonal' or old_value else ())
                + (('Trade tier:',) if variant != 'seasonal' else ()),
                report_absent=(label,) if variant != 'seasonal' and old_value is None else (),
                evidence=(
                    f'third-parties/d2data/json/base/uniqueitems.json:/{table}',
                    f'pricing/raw/d2data/uniqueitems.json:/{table}',
                ),
            )


CASES += tuple(additional_cases())
