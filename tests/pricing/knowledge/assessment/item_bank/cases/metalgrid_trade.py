"""Metalgrid ordinary candidacy, including best rolls without an invented premium."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Amulet', 'unique', 'Metalgrid', ((19, 0, 450), (31, 0, 350), *((s, 0, 35) for s in (39, 41, 43, 45))))


def cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.metalgrid_alternatives import amulet

    full = make_case('complete-perfect-no-price', amulet(350, 35, 450), 'candidate')
    yield replace(
        full,
        expected={
            **full.expected,
            'price_estimate': IsPartialDict(estimate_ist=None, unavailable_reason='no_matches', sellers=0),
        },
    )
    for ar, res, defense in product((400, 449, 450), (25, 34, 35), (300, 350)):
        raw = ((19, 0, ar), (31, 0, defense), *((s, 0, res) for s in (39, 41, 43, 45)))
        yield make_case(
            f'roll-{ar}-{res}-{defense}',
            replace(ITEM, raw_stats=raw),
            'candidate',
        )
    for key, lo, hi in ((19, 400, 450), (31, 300, 350), *((s, 25, 35) for s in (39, 41, 43, 45))):
        for value in (None, lo - 1, hi + 1):
            raw = tuple((s, p, value if s == key else v) for s, p, v in ITEM.raw_stats if s != key or value is not None)
            yield make_case(f'component-{key}-{value}', replace(ITEM, raw_stats=raw), 'unresolved')
    for key in (39, 41, 43, 45):
        raw = tuple((s, p, 25 if s == key else v) for s, p, v in ITEM.raw_stats)
        yield make_case(f'unequal-{key}', replace(ITEM, raw_stats=raw), 'unresolved')
    for label, changes in (
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unidentified', {'identified': False}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(ITEM, **changes), 'unresolved')


def make_case(label, specimen, status):
    qualified = status == 'candidate'
    return Case(
        id='metalgrid-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Metalgrid',),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': ['19:0', '31:0', '39:0', '41:0', '43:0', '45:0']} if qualified else {}),
            },
            'lines': [
                {
                    'text': ('Trade: ordinary candidate — Attack rating and all resistances support attack builds.'),
                    'tone': 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=('Trade tier: mid',) if qualified else (),
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
