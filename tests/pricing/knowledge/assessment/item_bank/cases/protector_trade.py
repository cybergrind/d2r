"""Protector's Stone: paired ED is one roll; other modifiers remain independent."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Colossal Jewel',
    'unique',
    "Protector's Stone",
    ((17, 0, 50), (18, 0, 50), (366, 0, 10), (85, 0, 5), (80, 0, 35), (79, 0, 50)),
)
KEYS = ['17:0', '18:0', '366:0', '85:0', '80:0', '79:0']


def make_case(label, item, qualified):
    status = 'candidate' if qualified else 'unresolved'
    return Case(
        id=f'protector-trade/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=(f'named:unique:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': KEYS} if qualified else {})},
            'lines': [
                {
                    'text': (
                        'Trade: ordinary candidate — Physical jewel demand; '
                        'no separate perfect-roll premium established.'
                    ),
                    'tone': 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only', 'Trade: premium candidate'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for ed, pierce, xp, mf, gold in product((30, 50), (5, 10), (3, 5), (15, 35), (25, 50)):
        raw = ((17, 0, ed), (18, 0, ed), (366, 0, pierce), (85, 0, xp), (80, 0, mf), (79, 0, gold))
        yield make_case(f'{ed}-{pierce}-{xp}-{mf}-{gold}', replace(ITEM, raw_stats=raw), True)
    for stat, values in (
        (17, (None, 29, 51, 30)),
        (18, (None, 29, 51, 30)),
        (366, (None, 4, 11)),
        (85, (None, 2, 6)),
        (80, (None, 14, 36)),
        (79, (None, 24, 51)),
    ):
        for value in values:
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None
            )
            yield make_case(f'stat-{stat}-{value}', replace(ITEM, raw_stats=raw), False)
    for label, changes in (
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(ITEM, **changes), False)


CASES = tuple(cases())
