"""Defender's Fire: joint perfect core versus independent secondary rolls."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Colossal Jewel', 'unique', "Defender's Fire", ((329, 0, 10), (333, 0, 10), (85, 0, 5), (80, 0, 35), (79, 0, 50))
)


def cases():
    for damage, pierce, xp, mf, gold in product((5, 9, 10), (5, 9, 10), (3, 5), (15, 35), (25, 50)):
        raw = ((329, 0, damage), (333, 0, pierce), (85, 0, xp), (80, 0, mf), (79, 0, gold))
        yield make_case(
            f'{damage}-{pierce}-{xp}-{mf}-{gold}',
            replace(ITEM, raw_stats=raw),
            'premium' if damage == pierce == 10 else 'candidate',
        )
    for stat, values in (
        (329, (None, 4, 11)),
        (333, (None, 4, 11)),
        (85, (None, 2, 6)),
        (80, (None, 14, 36)),
        (79, (None, 24, 51)),
    ):
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
    reason = (
        '10% fire skill damage and 10% fire pierce: premium asking segment.'
        if premium
        else 'Fire skill damage or pierce below 10%: ordinary trade candidate.'
    )
    return Case(
        id='defender-fire-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=("named:unique:Defender's Fire",),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': ['329:0', '333:0', '85:0', '80:0', '79:0']} if qualified else {}),
            },
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
