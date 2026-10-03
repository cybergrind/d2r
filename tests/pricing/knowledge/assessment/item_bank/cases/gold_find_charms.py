"""Independent end-to-end gold-find specimens, including overlapping keep uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECIMENS = (
    ('warcries-gold', 'Grand Charm', ((188, 34, 1), (79, 0, 30)), 'Warcries + gold find:'),
    ('warcries-gold', 'Grand Charm', ((188, 34, 1), (79, 0, 40)), 'Warcries + gold find:'),
    ('sharp-gold', 'Grand Charm', ((22, 0, 8), (19, 0, 49), (79, 0, 30)), 'Damage + attack rating + gold find:'),
    ('sharp-gold', 'Grand Charm', ((22, 0, 10), (19, 0, 76), (79, 0, 40)), 'Damage + attack rating + gold find:'),
    ('lucky-gold', 'Grand Charm', ((80, 0, 12), (79, 0, 40)), 'Magic find + gold find:'),
    ('grand-gold', 'Grand Charm', ((79, 0, 40),), 'Gold find: 40%'),
    (
        'shimmering-gold',
        'Small Charm',
        (*((s, 0, 5) for s in (39, 41, 43, 45)), (79, 0, 10)),
        'All resistances + gold find:',
    ),
    ('ruby-gold', 'Small Charm', ((39, 0, 11), (79, 0, 10)), 'Fire resistance + gold find:'),
    ('small-gold', 'Small Charm', ((79, 0, 10),), 'Gold find: 10%'),
)


def cases():
    for index, (watch, base, stats, text) in enumerate(SPECIMENS):
        item = Item(base, 'magic', raw_stats=stats, complete=True)
        for complete in (True, False):
            yield Case(
                id=f'gold-find-charms/{watch}/{index}/{complete}',
                item=replace(item, complete=complete),
                context={},
                scenario='positive' if complete else 'unknown',
                covers=(f'watch:{watch}',),
                expected={
                    'value_watch': Contains(IsPartialDict(details=IsPartialDict(watch_id=watch))) if complete else []
                },
                report_contains=('TRADE CANDIDATE', text) if complete else (),
                report_absent=() if complete else ('TRADE CANDIDATE',),
                evidence=('pricing/raw/mr/items__valuable-magic-items.html', 'pricing/raw/mr/planners/qx0106eh.json'),
            )


CASES = tuple(cases())


# These lower rolls must not acquire the stronger combination label. A retained
# plain resistance/gold-find use remains independently visible where applicable.
NEAR_MISSES = (
    ('warcries-gold', 'warcries-below-gold', 'Grand Charm', ((188, 34, 1), (79, 0, 29)), 'Warcries + gold find:', None),
    (
        'sharp-gold',
        'sharp-below-damage',
        'Grand Charm',
        ((22, 0, 7), (19, 0, 76), (79, 0, 30)),
        'Damage + attack rating + gold find:',
        None,
    ),
    (
        'sharp-gold',
        'sharp-below-gold',
        'Grand Charm',
        ((22, 0, 8), (19, 0, 49), (79, 0, 29)),
        'Damage + attack rating + gold find:',
        None,
    ),
    (
        'shimmering-gold',
        'shimmering-below-gold',
        'Small Charm',
        (*((s, 0, 5) for s in (39, 41, 43, 45)), (79, 0, 9)),
        'All resistances + gold find:',
        'plain-res-5',
    ),
    (
        'lucky-gold',
        'lucky-below-mf',
        'Grand Charm',
        ((80, 0, 11), (79, 0, 40)),
        'Magic find + gold find:',
        'grand-gold',
    ),
    (
        'ruby-gold',
        'ruby-below-res',
        'Small Charm',
        ((39, 0, 10), (79, 0, 10)),
        'Fire resistance + gold find:',
        'small-gold',
    ),
    ('grand-gold', 'grand-below-gold', 'Grand Charm', ((79, 0, 39),), 'Gold find: 40%', None),
    ('small-gold', 'small-below-gold', 'Small Charm', ((79, 0, 9),), 'Gold find: 10%', None),
)
CASES += tuple(
    Case(
        id=f'gold-find-charms/{name}',
        item=Item(base, 'magic', raw_stats=stats, complete=True),
        context={},
        scenario='negative',
        covers=(f'watch:{watch}',),
        expected={'value_watch': Contains(IsPartialDict(details=IsPartialDict(watch_id=fallback))) if fallback else []},
        report_contains=('TRADE CANDIDATE',) if fallback else (),
        report_absent=(label,),
        evidence=('pricing/raw/mr/items__valuable-magic-items.html', 'pricing/raw/mr/planners/qx0106eh.json'),
    )
    for watch, name, base, stats, label, fallback in NEAR_MISSES
)
