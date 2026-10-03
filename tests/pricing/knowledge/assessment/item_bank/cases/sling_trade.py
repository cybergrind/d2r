"""Sling's pierce threshold, independent secondary rolls and variant boundaries."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Ring', 'unique', 'Sling', ((358, 0, 5), (1, 0, 15), (80, 0, 20)))


def cases():
    for pierce, energy, mf in product((3, 4, 5), (10, 11, 15), (10, 11, 20)):
        specimen = replace(ITEM, raw_stats=((358, 0, pierce), (1, 0, energy), (80, 0, mf)))
        yield make_case(f'{pierce}-{energy}-{mf}', specimen, 'premium' if pierce == 5 else 'candidate')
    for stat, values in ((358, (None, 2, 6)), (1, (None, 9, 16)), (80, (None, 9, 21))):
        for value in values:
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None
            )
            yield make_case(f'stat-{stat}-{value}', replace(ITEM, raw_stats=raw), 'unresolved')
    for label, changes in (
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(ITEM, **changes), 'unresolved')


def make_case(label, item, status):
    qualified = status != 'unresolved'
    premium = status == 'premium'
    reason = '5% magic pierce: higher-demand roll.' if premium else '3\u20134% magic pierce: ordinary trade candidate.'
    return Case(
        id='sling-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Sling',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['358:0', '1:0', '80:0']} if qualified else {})},
            'lines': [
                {
                    'text': f'Trade: {"premium" if premium else "ordinary"} candidate — {reason}',
                    'tone': 'tier_high' if premium else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
