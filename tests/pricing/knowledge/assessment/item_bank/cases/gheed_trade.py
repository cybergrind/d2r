"""Gheed MF segment and independent gold/discount validity through reports."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Grand Charm', 'unique', "Gheed's Fortune", ((80, 0, 40), (79, 0, 160), (87, 0, 15)))


def cases():
    for mf, gold, discount in product((20, 38, 39, 40), (80, 160), (10, 15)):
        status = 'premium' if mf == 40 else 'candidate'
        yield make_case(
            f'roll-{mf}-{gold}-{discount}',
            replace(ITEM, raw_stats=((80, 0, mf), (79, 0, gold), (87, 0, discount))),
            status,
        )
    for key, lo, hi in ((80, 20, 40), (79, 80, 160), (87, 10, 15)):
        for value in (None, lo - 1, hi + 1):
            raw = tuple((s, p, value if s == key else v) for s, p, v in ITEM.raw_stats if s != key or value is not None)
            yield make_case(f'component-{key}-{value}', replace(ITEM, raw_stats=raw), 'unresolved')
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
    qualified = status != 'unresolved'
    reason = (
        '40% magic find: perfect-MF premium asking segment.'
        if status == 'premium'
        else 'Ordinary magic-find segment; premium magic-find demand requires 40%.'
    )
    text = 'Trade: ' + ('premium' if status == 'premium' else 'ordinary') + ' candidate — ' + reason
    return Case(
        id='gheed-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=("named:unique:Gheed's Fortune",),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['80:0', '79:0', '87:0']} if qualified else {})},
            'lines': [{'text': text, 'tone': 'tier_high' if status == 'premium' else 'tier_low'}] if qualified else [],
        },
        report_contains=('Trade tier: high' if status == 'premium' else 'Trade tier: mid',) if qualified else (),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
