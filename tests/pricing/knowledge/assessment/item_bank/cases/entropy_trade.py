"""Entropy Locket's five legal roll axes do not imply a perfect-roll premium."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Amulet', 'unique', 'Entropy Locket', ((357, 0, 10), (105, 0, 10), (41, 0, 40), (77, 0, 15), (35, 0, 12)))


def cases():
    for magic, fcr, resist, mana, mdr in product((5, 6, 10), (5, 6, 10), (25, 26, 40), (10, 11, 15), (8, 9, 12)):
        raw = ((357, 0, magic), (105, 0, fcr), (41, 0, resist), (77, 0, mana), (35, 0, mdr))
        yield make_case(f'{magic}-{fcr}-{resist}-{mana}-{mdr}', replace(ITEM, raw_stats=raw), True)
    for stat, values in (
        (357, (None, 4, 11)),
        (105, (None, 4, 11)),
        (41, (None, 24, 41)),
        (77, (None, 9, 16)),
        (35, (None, 7, 13)),
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


def make_case(label, item, qualified):
    status = 'candidate' if qualified else 'unresolved'
    return Case(
        id='entropy-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Entropy Locket',),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': ['357:0', '105:0', '41:0', '77:0', '35:0']} if qualified else {}),
            },
            'lines': [
                {
                    'text': (
                        'Trade: ordinary candidate — Caster-amulet demand; '
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


CASES = tuple(cases())
