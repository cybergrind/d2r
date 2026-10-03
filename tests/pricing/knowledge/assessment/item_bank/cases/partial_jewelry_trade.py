"""Reviewed trade segments preserve unknown lower rolls and reject invalid stats."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


MARA_STATS = ((127, 0, 2), *((s, 0, 5) for s in (0, 1, 2, 3)))
MARA = Item(
    'Amulet', 'unique', "Mara's Kaleidoscope", (*MARA_STATS, *((s, 0, 30) for s in (39, 41, 43, 45))), complete=True
)
NAGEL = Item('Ring', 'unique', 'Nagelring', ((35, 0, 3), (78, 0, 3), (19, 0, 75), (80, 0, 30)), complete=True)
VARIANTS = (
    ('ethereal', {'ethereal': True}),
    ('unknown-ethereal', {'ethereal': None}),
    ('unidentified', {'identified': False}),
    ('socketed', {'sockets': 1}),
    ('unknown-sockets', {'sockets': None}),
    ('unknown-contents', {'socket_contents': 'unknown'}),
)


def make_case(slug, label, item, status):
    mara = slug == 'mara'
    material = ['39:0', '41:0', '43:0', '45:0'] if mara else ['80:0', '19:0']
    reason = (
        '30 all resistances: perfect shared-roll premium candidate.'
        if status == 'premium'
        else '27-29 all resistances: ordinary trade candidate; premium requires 30.'
        if mara
        else '30% magic find: ordinary low-tier trade candidate; no verified perfect-AR premium.'
    )
    qualified = status != 'unresolved'
    label_status = 'premium candidate' if status == 'premium' else 'ordinary candidate'
    return Case(
        id=f'{slug}-partial-trade/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=(f'named:unique:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': material} if qualified else {})},
            'lines': [
                {
                    'text': f'Trade: {label_status} — {reason}',
                    'tone': 'tier_high' if status == 'premium' else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def mara_cases():
    for res in range(20, 31):
        item = replace(MARA, raw_stats=(*MARA_STATS, *((s, 0, res) for s in (39, 41, 43, 45))))
        status = 'premium' if res == 30 else 'candidate' if res >= 27 else 'unresolved'
        yield make_case('mara', f'res-{res}', item, status)
    for res in (19, 31):
        item = replace(MARA, raw_stats=(*MARA_STATS, *((s, 0, res) for s in (39, 41, 43, 45))))
        yield make_case('mara', f'res-{res}', item, 'unresolved')
    for key in (39, 41, 43, 45):
        for value in (None, 19, 31, 20):
            raw = tuple((s, p, value if s == key else v) for s, p, v in MARA.raw_stats if s != key or value is not None)
            yield make_case('mara', f'component-{key}-{value}', replace(MARA, raw_stats=raw), 'unresolved')
    for label, changes in VARIANTS:
        yield make_case('mara', label, replace(MARA, **changes), 'unresolved')


def nagel_cases():
    for mf, ar in product(range(15, 31), (50, 74, 75)):
        item = replace(NAGEL, raw_stats=((35, 0, 3), (78, 0, 3), (19, 0, ar), (80, 0, mf)))
        yield make_case('nagel', f'mf-{mf}-ar-{ar}', item, 'candidate' if mf == 30 else 'unresolved')
    for key, low, high in ((19, 50, 75), (80, 15, 30)):
        for value in (None, low - 1, high + 1):
            raw = tuple(
                (s, p, value if s == key else v) for s, p, v in NAGEL.raw_stats if s != key or value is not None
            )
            yield make_case('nagel', f'component-{key}-{value}', replace(NAGEL, raw_stats=raw), 'unresolved')
    for label, changes in VARIANTS:
        yield make_case('nagel', label, replace(NAGEL, **changes), 'unresolved')


MARA_CASES = tuple(mara_cases())
NAGEL_CASES = tuple(nagel_cases())
CASES = (*MARA_CASES, *NAGEL_CASES)
