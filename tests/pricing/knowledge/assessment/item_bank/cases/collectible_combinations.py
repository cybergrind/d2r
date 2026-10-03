"""Independent native examples of valuable multi-modifier charm/jewel demand."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('shimmering-balance', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (99, 0, 5)), 99, 4),
    ('shimmering-inertia', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (96, 0, 3)), 96, 2),
    ('shimmering-sustenance', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (7, 0, 3840)), 39, 3),
    ('fine-sustenance', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 3840)), 19, 9),
    ('fine-low-life', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 2560)), 19, 9),
    ('snake-sustenance', 'Small Charm', ((9, 0, 3072), (7, 0, 3840)), 9, 2304),
    ('realgar-fervor', 'Jewel', ((17, 0, 29), (18, 0, 29), (93, 0, 15)), 93, 0),
    ('serpent-life', 'Small Charm', ((9, 0, 4352), (7, 0, 5120)), 9, 3072),
    ('scintillating-freedom', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (91, 0, -15)), 91, -14),
    ('scintillating-hope', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (7, 0, 5120)), 7, 3584),
    *(
        (f'scintillating-{attribute}', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (stat, 0, 9)), stat, 4)
        for attribute, stat in (('strength', 0), ('dexterity', 2), ('energy', 1))
    ),
    *(
        (f'{element}-good-luck', 'Small Charm', ((stat, 0, 11), (80, 0, 7)), stat, 7)
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    *(
        (f'{element}-life', 'Small Charm', ((stat, 0, 11), (7, 0, 5120)), stat, 7)
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    ('shimmering-good-luck', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (80, 0, 7)), 80, 5),
    ('fine-good-luck', 'Small Charm', ((22, 0, 3), (19, 0, 20), (80, 0, 7)), 22, 1),
    ('grand-shimmering-life', 'Grand Charm', (*((s, 0, 15) for s in (39, 41, 43, 45)), (7, 0, 11520)), 39, 12),
    ('grand-shimmering-sustenance', 'Grand Charm', (*((s, 0, 15) for s in (39, 41, 43, 45)), (7, 0, 7424)), 7, 4864),
    ('sharp-sustenance', 'Grand Charm', ((22, 0, 10), (19, 0, 76), (7, 0, 7424)), 22, 7),
    ('fine-life', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 5120)), 19, 9),
    ('sharp-life', 'Grand Charm', ((22, 0, 10), (19, 0, 76), (7, 0, 11520)), 22, 7),
    ('shimmering-life', 'Small Charm', ((39, 0, 5), (41, 0, 5), (43, 0, 5), (45, 0, 5), (7, 0, 5120)), 39, 3),
    ('ruby-fervor', 'Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15)), 93, 0),
    ('scintillating-fervor', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (93, 0, 15)), 93, 0),
    ('ruby-fire-fervor', 'Jewel', ((39, 0, 30), (93, 0, 15)), 39, 19),
    ('large-sharp-life', 'Large Charm', ((22, 0, 6), (19, 0, 48), (7, 0, 8960)), 22, 4),
    ('large-shimmering-life', 'Large Charm', (*((s, 0, 8) for s in (39, 41, 43, 45)), (7, 0, 8960)), 7, 4864),
)

MINIMUMS = {
    'shimmering-balance': (*((s, 0, 4) for s in (39, 41, 43, 45)), (99, 0, 5)),
    'shimmering-inertia': (*((s, 0, 4) for s in (39, 41, 43, 45)), (96, 0, 3)),
    'shimmering-sustenance': (*((s, 0, 4) for s in (39, 41, 43, 45)), (7, 0, 2560)),
    'fine-sustenance': ((22, 0, 3), (19, 0, 10), (7, 0, 2816)),
    'fine-low-life': ((22, 0, 3), (19, 0, 10), (7, 0, 1280)),
    'snake-sustenance': ((9, 0, 2560), (7, 0, 2816)),
    'realgar-fervor': ((17, 0, 20), (18, 0, 20), (93, 0, 15)),
    'serpent-life': ((9, 0, 3328), (7, 0, 4096)),
    'scintillating-freedom': (*((s, 0, 11) for s in (39, 41, 43, 45)), (91, 0, -15)),
    'scintillating-hope': (*((s, 0, 12) for s in (39, 41, 43, 45)), (7, 0, 3840)),
    **{
        f'scintillating-{attribute}': (*((s, 0, 12) for s in (39, 41, 43, 45)), (stat, 0, 5))
        for attribute, stat in (('strength', 0), ('dexterity', 2), ('energy', 1))
    },
    **{
        f'{element}-good-luck': ((stat, 0, 8), (80, 0, 6))
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    },
    **{
        f'{element}-life': ((stat, 0, 8), (7, 0, 4096))
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    },
    'shimmering-good-luck': (*((s, 0, 4) for s in (39, 41, 43, 45)), (80, 0, 6)),
    'fine-good-luck': ((22, 0, 2), (19, 0, 10), (80, 0, 6)),
    'grand-shimmering-life': (*((s, 0, 13) for s in (39, 41, 43, 45)), (7, 0, 7680)),
    'grand-shimmering-sustenance': (*((s, 0, 13) for s in (39, 41, 43, 45)), (7, 0, 5120)),
    'sharp-sustenance': ((22, 0, 8), (19, 0, 49), (7, 0, 5120)),
    'fine-life': ((22, 0, 3), (19, 0, 10), (7, 0, 4096)),
    'sharp-life': ((22, 0, 8), (19, 0, 49), (7, 0, 7680)),
    'shimmering-life': (*((s, 0, 4) for s in (39, 41, 43, 45)), (7, 0, 4096)),
    'ruby-fervor': ((17, 0, 30), (18, 0, 30), (93, 0, 15)),
    'scintillating-fervor': (*((s, 0, 11) for s in (39, 41, 43, 45)), (93, 0, 15)),
    'ruby-fire-fervor': ((39, 0, 20), (93, 0, 15)),
    'large-sharp-life': ((22, 0, 5), (19, 0, 21), (7, 0, 5120)),
    'large-shimmering-life': (*((s, 0, 7) for s in (39, 41, 43, 45)), (7, 0, 5120)),
}


def cases():
    for watch_id, base, stats, decisive, lower in EXAMPLES:
        item = Item(base, 'magic', raw_stats=stats, complete=True)
        for label, specimen, positive in (
            ('top-combination', item, True),
            ('minimum-combination', replace(item, raw_stats=MINIMUMS[watch_id]), True),
            (
                'near-miss',
                replace(item, raw_stats=tuple((s, layer, lower if s == decisive else v) for s, layer, v in stats)),
                False,
            ),
            ('missing-modifier', replace(item, raw_stats=tuple(r for r in stats if r[0] != decisive)), False),
            ('incomplete', replace(item, complete=False), False),
        ):
            # Losing FHR/FRW defeats the combined rule, but five all resistance
            # still has its independently evidenced plain-charm priority.
            plain = watch_id in ('shimmering-balance', 'shimmering-inertia', 'shimmering-good-luck') and label in (
                'near-miss',
                'missing-modifier',
            )
            wanted = 'plain-res-5' if plain else watch_id
            valuable = positive or plain
            yield Case(
                id=f'collectible-combination/{watch_id}/{label}',
                item=specimen,
                context={},
                scenario='positive' if positive else 'unknown' if label == 'incomplete' else 'negative',
                covers=(f'watch:{watch_id}',),
                expected={
                    'value_watch': Contains(IsPartialDict(details=IsPartialDict(watch_id=wanted))) if valuable else []
                },
                report_contains=('TRADE CANDIDATE', 'All resistances: 5')
                if plain
                else ('TRADE CANDIDATE',)
                if positive
                else (),
                report_absent=() if valuable else ('TRADE CANDIDATE',),
                evidence=('pricing/raw/mr/items__valuable-magic-items.html',),
            )


def damage_ias_boundaries():
    for damage, watch, band in (
        (19, None, None),
        (20, 'realgar-fervor', '20-29% ED'),
        (21, 'realgar-fervor', '20-29% ED'),
        (29, 'realgar-fervor', '20-29% ED'),
        (30, 'ruby-fervor', '30-40% ED'),
        (31, 'ruby-fervor', '30-40% ED'),
        (40, 'ruby-fervor', '30-40% ED'),
        (41, None, None),
    ):
        yield Case(
            id=f'collectible-combination/damage-ias-boundary/{damage}',
            item=Item('Jewel', 'magic', raw_stats=((17, 0, damage), (18, 0, damage), (93, 0, 15)), complete=True),
            context={},
            scenario='positive' if watch else 'negative',
            covers=('watch:realgar-fervor', 'watch:ruby-fervor'),
            expected={'value_watch': [IsPartialDict(details=IsPartialDict(watch_id=watch))] if watch else []},
            report_contains=('TRADE CANDIDATE', band) if watch else (),
            report_absent=() if watch else ('TRADE CANDIDATE',),
            evidence=('pricing/raw/mr/items__valuable-magic-items.html',),
        )


def low_level_jewels():
    for watch, prefix, top, minimum, near in (
        (
            'rusty-carnage',
            196,
            ((17, 0, 20), (18, 0, 20), (22, 0, 15)),
            ((17, 0, 18), (18, 0, 18), (22, 0, 14)),
            ((17, 0, 17), (18, 0, 17), (22, 0, 14)),
        ),
        ('carbuncle-carnage', 183, ((22, 0, 20),), ((22, 0, 18),), ((22, 0, 17),)),
    ):
        item = Item('Jewel', 'magic', raw_stats=top, affix_records=(('prefix', prefix), ('suffix', 222)), complete=True)
        for label, specimen, positive in (
            ('top', item, True),
            ('minimum', replace(item, raw_stats=minimum), True),
            ('near-miss', replace(item, raw_stats=near), False),
            ('unknown-affixes', replace(item, affix_records=None), False),
            ('higher-level-affixes', replace(item, affix_records=(('prefix', 185), ('suffix', 221))), False),
            ('incomplete', replace(item, complete=False), False),
        ):
            yield Case(
                id=f'collectible-combination/{watch}/{label}',
                item=specimen,
                context={},
                scenario='positive'
                if positive
                else 'unknown'
                if label in ('unknown-affixes', 'incomplete')
                else 'negative',
                covers=(f'watch:{watch}',),
                expected={'value_watch': [IsPartialDict(details=IsPartialDict(watch_id=watch))] if positive else []},
                report_contains=('TRADE CANDIDATE', 'Level-18 jewel') if positive else (),
                report_absent=() if positive else ('Level-18 jewel',),
                evidence=('pricing/raw/mr/items__valuable-magic-items.html',),
            )


def poison_charms():
    for watch, suffix, rate, frames in (('pestilent-life', 349, 299, 150), ('pestilent-anthrax', 693, 385, 300)):
        stats = ((57, 0, rate), (58, 0, rate), (59, 0, frames)) + (((7, 0, 5120),) if suffix == 349 else ())
        item = Item(
            'Small Charm', 'magic', raw_stats=stats, affix_records=(('prefix', 661), ('suffix', suffix)), complete=True
        )
        specimens = [
            ('top', item, True),
            ('wrong-rate', replace(item, raw_stats=((57, 0, rate - 1), *stats[1:])), False),
            (
                'wrong-duration',
                replace(item, raw_stats=tuple((s, p, v - 25 if s == 59 else v) for s, p, v in stats)),
                False,
            ),
            ('missing-rate', replace(item, raw_stats=stats[1:]), False),
            ('unknown-affixes', replace(item, affix_records=None), False),
            ('incomplete', replace(item, complete=False), False),
        ]
        if suffix == 349:
            specimens.extend(
                [
                    ('minimum-life', replace(item, raw_stats=(*stats[:3], (7, 0, 4096))), True),
                    ('near-life', replace(item, raw_stats=(*stats[:3], (7, 0, 3840))), False),
                ]
            )
        for label, specimen, positive in specimens:
            yield Case(
                id=f'collectible-combination/{watch}/{label}',
                item=specimen,
                context={},
                scenario='positive'
                if positive
                else 'unknown'
                if label in ('unknown-affixes', 'incomplete')
                else 'negative',
                covers=(f'watch:{watch}',),
                expected={'value_watch': [IsPartialDict(details=IsPartialDict(watch_id=watch))] if positive else []},
                report_contains=('TRADE CANDIDATE', 'Pestilent') if positive else (),
                report_absent=() if positive else ('TRADE CANDIDATE',),
                evidence=('pricing/raw/mr/items__valuable-magic-items.html',),
            )


def shocking_charms():
    item = Item(
        'Small Charm',
        'magic',
        raw_stats=((50, 0, 1), (51, 0, 71), (7, 0, 5120)),
        affix_records=(('prefix', 649), ('suffix', 349)),
        complete=True,
    )
    for label, specimen, positive in (
        ('top', item, True),
        ('minimum', replace(item, raw_stats=((50, 0, 1), (51, 0, 44), (7, 0, 4096))), True),
        ('lower-damage', replace(item, raw_stats=((50, 0, 1), (51, 0, 43), (7, 0, 5120))), False),
        ('lower-life', replace(item, raw_stats=((50, 0, 1), (51, 0, 71), (7, 0, 3840))), False),
        ('missing-damage-minimum', replace(item, raw_stats=item.raw_stats[1:]), False),
        ('wrong-affix', replace(item, affix_records=(('prefix', 648), ('suffix', 349))), False),
        ('unknown-affixes', replace(item, affix_records=None), False),
        ('incomplete', replace(item, complete=False), False),
    ):
        yield Case(
            id=f'collectible-combination/shocking-life/{label}',
            item=specimen,
            context={},
            scenario='positive'
            if positive
            else 'unknown'
            if label in ('unknown-affixes', 'incomplete')
            else 'negative',
            covers=('watch:shocking-life',),
            expected={
                'value_watch': [IsPartialDict(details=IsPartialDict(watch_id='shocking-life'))] if positive else []
            },
            report_contains=('TRADE CANDIDATE', 'Shocking lightning damage + life') if positive else (),
            report_absent=() if positive else ('TRADE CANDIDATE',),
            evidence=('pricing/raw/mr/items__valuable-magic-items.html',),
        )


CASES = (*cases(), *damage_ias_boundaries(), *low_level_jewels(), *poison_charms(), *shocking_charms())


def plain_resistance_cases():
    for resistance, tier in ((3, 'Low'), (4, 'Medium'), (5, 'High')):
        for life in (None, 9):
            stats = tuple((s, 0, resistance) for s in (39, 41, 43, 45))
            if life is not None:
                stats += ((7, 0, life * 256),)
            yield Case(
                id=f'plain-resistance/{resistance}/{life}',
                item=Item('Small Charm', 'magic', raw_stats=stats, complete=True),
                context={},
                scenario='positive',
                covers=(f'watch:plain-res-{resistance}',),
                expected={
                    'value_watch': Contains(
                        IsPartialDict(details=IsPartialDict(watch_id=f'plain-res-{resistance}', guide_tier=tier))
                    )
                },
                report_contains=('TRADE CANDIDATE', f'All resistances: {resistance}'),
                evidence=('pricing/raw/mr/planners/qx0106eh.json',),
            )


CASES = (*CASES, *plain_resistance_cases())


def plain_resistance_boundaries():
    for resistance in (3, 4, 5):
        for scenario in ('negative', 'unknown'):
            observed = resistance - 1 if scenario == 'negative' else resistance
            fallback = f'plain-res-{observed}' if scenario == 'negative' and observed >= 3 else None
            yield Case(
                id=f'plain-resistance/{resistance}/{scenario}',
                item=Item(
                    'Small Charm',
                    'magic',
                    raw_stats=tuple((stat, 0, observed) for stat in (39, 41, 43, 45)),
                    complete=scenario != 'unknown',
                ),
                context={},
                scenario=scenario,
                covers=(f'watch:plain-res-{resistance}',),
                expected={
                    'value_watch': [IsPartialDict(details=IsPartialDict(watch_id=fallback))] if fallback else [],
                },
                report_contains=('TRADE CANDIDATE', f'All resistances: {observed}') if fallback else (),
                report_absent=(f'All resistances: {resistance}; 0-9 life',) if fallback else ('TRADE CANDIDATE',),
                evidence=('pricing/raw/mr/items__valuable-magic-items.html', 'pricing/raw/mr/planners/qx0106eh.json'),
            )


CASES = (*CASES, *plain_resistance_boundaries())
