"""Paired elemental rolls, all resistance and socket premiums from offline evidence.

Partial captures intentionally do not justify numeric prices. A baseline high tier
is distinct from a verified perfect-roll segment (notably Griffon's Eye).
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SOURCES = {
    "Griffon's Eye": (336, 'UQ-griffon-s-eye'),
    "Mara's Kaleidoscope": (272, 'UQ-mara-s-kaleidoscope'),
    "Death's Web": (299, 'UQ-death-s-web'),
    'Crown of Ages': (344, 'UQ-crown-of-ages'),
}


def specimen(name, base, label, stats, scenario, tier, report_stat, *, sockets=0, variant=None, report_absent=()):
    native_id, research = SOURCES[name]
    expectation = {'status': 'reviewed', 'tier': tier}
    if variant is not None:
        expectation['variant'] = IsPartialDict(**variant)
    return Case(
        id=f'named-caster-premium/{name}/{label}',
        item=Item(base, 'unique', name, tuple(stats), sockets=sockets),
        context={},
        scenario=scenario,
        covers=('named:unique:' + name,),
        expected={
            'assessment': IsPartialDict(trade_tier=IsPartialDict(**expectation)),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        report_contains=(name, 'Trade tier: ' + ('mid' if tier == 'med' else tier), report_stat),
        report_absent=report_absent,
        evidence=(
            f'third-parties/d2data/json/uniqueitems.json:/{native_id}',
            'pricing/data/wp-i-uniques-misc.json:/' + research,
        ),
    )


def all_res(value):
    return tuple((stat, 0, value) for stat in (39, 41, 43, 45))


def cases():
    fixed = ((127, 0, 1), (105, 0, 25))
    for label, rolls, scenario, variant in (
        (
            'both-perfect',
            ((334, 0, 20), (330, 0, 15)),
            'positive',
            {
                'status': 'reviewed',
                'reasons': Contains('Perfect lightning pierce and skill damage: top asking segment'),
            },
        ),
        (
            'one-perfect',
            ((334, 0, 20), (330, 0, 14)),
            'positive',
            {'status': 'reviewed', 'reasons': Contains('One perfect lightning roll: premium asking segment')},
        ),
        ('neither-perfect', ((334, 0, 19), (330, 0, 14)), 'negative', {'status': 'reviewed', 'reasons': []}),
        ('unknown-rolls', (), 'unknown', {'status': 'conditional', 'tier': None}),
    ):
        yield specimen(
            "Griffon's Eye",
            'Diadem',
            label,
            (*fixed, *rolls),
            scenario,
            'high',
            '(15-20%)' if rolls else 'Faster Cast Rate',
            variant=variant,
        )

    fixed = ((127, 0, 2), (0, 0, 5), (1, 0, 5), (2, 0, 5), (3, 0, 5))
    for label, rolls, scenario, tier in (
        ('perfect', all_res(30), 'positive', 'high'),
        ('reviewed-band-boundary', all_res(27), 'positive', 'high'),
        ('below-reviewed-band', all_res(26), 'negative', 'med'),
        ('missing-poison-resistance', all_res(30)[:3], 'unknown', 'med'),
    ):
        yield specimen("Mara's Kaleidoscope", 'Amulet', label, (*fixed, *rolls), scenario, tier, '(20-30%)')

    fixed = ((127, 0, 2), (138, 0, 7), (86, 0, 7))
    for label, rolls, scenario, tier in (
        ('perfect-pair', ((336, 0, 50), (188, 17, 2)), 'positive', 'high'),
        ('one-pierce-short', ((336, 0, 49), (188, 17, 2)), 'negative', 'med'),
        ('one-tab-rank-short', ((336, 0, 50), (188, 17, 1)), 'negative', 'med'),
        ('unknown-tab-ranks', ((336, 0, 50),), 'unknown', 'med'),
    ):
        yield specimen("Death's Web", 'Unearthed Wand', label, (*fixed, *rolls), scenario, tier, '(40-50%)')

    fixed = ((127, 0, 1), (99, 0, 30), (152, 0, 1), (16, 0, 50))
    for label, sockets, resist, dr, scenario, tier in (
        ('two-socket-perfect', 2, 30, 15, 'positive', 'high'),
        ('two-socket-low-rolls', 2, 20, 10, 'positive', 'high'),
        ('one-socket-perfect-rolls', 1, 30, 15, 'negative', 'med'),
        ('unknown-sockets', None, 30, 15, 'unknown', 'med'),
    ):
        stats = (*fixed, *all_res(resist), (36, 0, dr))
        if sockets is not None:
            stats += ((194, 0, sockets),)
        yield specimen(
            'Crown of Ages',
            'Corona',
            label,
            stats,
            scenario,
            tier,
            'item range: 10-15' if sockets is None else '(10-15%)',
            sockets=sockets,
            report_absent=('15% (10-15%)',) if sockets is None else (),
        )


def socket_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.facet_shields import facet

    child = facet('lightning', 5)
    for label, pierce, mastery, payload, scenario in (
        ('filled-perfect', 25, 20, child, 'positive'),
        ('filled-nonperfect', 24, 19, child, 'negative'),
        ('unknown-facet-capture', 25, 20, replace(child, complete=False), 'unknown'),
        ('unknown-parent-capture', 25, 20, child, 'unknown'),
    ):
        known = scenario != 'unknown'
        variant = {'tier': 'high' if known else None}
        if known:
            variant['intrinsic_rolls'] = IsPartialDict(
                {
                    '330:0': IsPartialDict(intrinsic=mastery - 5),
                    '334:0': IsPartialDict(intrinsic=pierce - 5),
                }
            )
            variant['reasons'] = (
                Contains('Perfect lightning pierce and skill damage: top asking segment')
                if scenario == 'positive'
                else []
            )
        yield Case(
            id='named-caster-premium/Griffon-socket/' + label,
            item=Item(
                'Diadem',
                'unique',
                "Griffon's Eye",
                (
                    (31, 0, 160),
                    (72, 0, 20),
                    (73, 0, 20),
                    (127, 0, 1),
                    (105, 0, 25),
                    (334, 0, pierce),
                    (330, 0, mastery),
                    (50, 0, 1),
                    (51, 0, 74),
                    (197, 53 * 64 + 47, 100),
                    (194, 0, 1),
                ),
                complete=label != 'unknown-parent-capture',
                sockets=1,
                socket_contents='filled',
                socket_items=(payload,),
            ),
            context={},
            scenario=scenario,
            covers=("named:unique:Griffon's Eye",),
            expected={
                'assessment': IsPartialDict(trade_tier=IsPartialDict(tier='high', variant=IsPartialDict(**variant))),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
            report_contains=("Griffon's Eye", 'Rainbow Facet', 'Trade tier: high'),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/336',
                'third-parties/d2data/json/uniqueitems.json:/392',
                'pricing/data/wp-i-uniques-misc.json:/UQ-griffon-s-eye',
            ),
        )


CASES = (*cases(), *socket_cases())
