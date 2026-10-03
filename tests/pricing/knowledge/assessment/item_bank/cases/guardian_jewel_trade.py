"""Guardian jewels distinguish joint-perfect core rolls from ordinary demand."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


VARIANTS = (
    ('light', "Guardian's Light", 357, 358, 'Magic'),
    ('thunder', "Guardian's Thunder", 330, 334, 'Lightning'),
)


def cases():
    for slug, name, damage_stat, pierce_stat, kind in VARIANTS:
        item = Item(
            'Colossal Jewel',
            'unique',
            name,
            ((damage_stat, 0, 10), (pierce_stat, 0, 10), (85, 0, 5), (80, 0, 35), (79, 0, 50)),
        )
        for damage, pierce, xp, mf, gold in product((5, 9, 10), (5, 9, 10), (3, 5), (15, 35), (25, 50)):
            raw = ((damage_stat, 0, damage), (pierce_stat, 0, pierce), (85, 0, xp), (80, 0, mf), (79, 0, gold))
            yield make_case(slug, f'{damage}-{pierce}-{xp}-{mf}-{gold}', replace(item, raw_stats=raw), kind, True)
        for stat, values in (
            (damage_stat, (None, 4, 11)),
            (pierce_stat, (None, 4, 11)),
            (85, (None, 2, 6)),
            (80, (None, 14, 36)),
            (79, (None, 24, 51)),
        ):
            for value in values:
                raw = tuple(
                    (s, p, value if s == stat else v) for s, p, v in item.raw_stats if s != stat or value is not None
                )
                yield make_case(slug, f'stat-{stat}-{value}', replace(item, raw_stats=raw), kind, False)
        for label, changes in (
            ('unidentified', {'identified': False}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
        ):
            yield make_case(slug, label, replace(item, **changes), kind, False)


def make_case(slug, label, item, kind, qualified):
    premium = qualified and item.raw_stats[0][2] == item.raw_stats[1][2] == 10
    status = 'premium' if premium else 'candidate' if qualified else 'unresolved'
    reason = (
        f'10% {kind.lower()} skill damage and 10% {kind.lower()} pierce: premium asking segment.'
        if premium
        else f'{kind} skill damage or pierce below 10%: ordinary trade candidate.'
    )
    keys = ['357:0', '358:0', '85:0', '80:0', '79:0'] if slug == 'light' else ['330:0', '334:0', '85:0', '80:0', '79:0']
    return Case(
        id=f'guardian-jewel-trade/{slug}/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=(f'named:unique:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': keys} if qualified else {})},
            'lines': [
                {
                    'text': f'Trade: {"premium" if premium else "ordinary"} candidate — {reason}',
                    'tone': 'tier_high' if premium else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',) if premium else ('Trade: use only', 'Trade: premium candidate'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
