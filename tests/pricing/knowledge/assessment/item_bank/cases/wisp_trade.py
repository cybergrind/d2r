"""Joint lightning-absorb/magic-find trade boundaries, independent of build roles."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Ring', 'unique', 'Wisp Projector', ((144, 0, 20), (80, 0, 20)))
ORDINARY = 'Ordinary roll; premium requires 20% lightning absorb and 20% magic find.'
PREMIUM = '20% lightning absorb and 20% magic find: double-perfect premium asking segment.'


def cases():
    for absorb, mf in product((10, 19, 20), (10, 19, 20)):
        status = 'premium' if (absorb, mf) == (20, 20) else 'candidate'
        yield make_case(f'absorb-{absorb}-mf-{mf}', replace(ITEM, raw_stats=((144, 0, absorb), (80, 0, mf))), status)
    for key, values in ((144, (9, 21, None)), (80, (9, 21, None))):
        for value in values:
            stats = tuple(
                (stat, layer, value if stat == key else raw)
                for stat, layer, raw in ITEM.raw_stats
                if stat != key or value is not None
            )
            yield make_case(f'stat-{key}-{value}', replace(ITEM, raw_stats=stats), 'unresolved')
    for label, item in (
        ('unidentified', replace(ITEM, identified=False)),
        ('ethereal', replace(ITEM, ethereal=True)),
        ('unknown-ethereal', replace(ITEM, ethereal=None)),
        ('socketed', replace(ITEM, sockets=1)),
        ('unknown-sockets', replace(ITEM, sockets=None)),
        ('unknown-contents', replace(ITEM, socket_contents='unknown')),
    ):
        yield make_case(label, item, 'unresolved')


def make_case(label, item, status):
    qualified = status != 'unresolved'
    lines = []
    if qualified:
        premium = status == 'premium'
        lines = [
            {
                'text': 'Trade: '
                + ('premium' if premium else 'ordinary')
                + ' candidate — '
                + (PREMIUM if premium else ORDINARY),
                'tone': 'tier_high' if premium else 'tier_low',
            }
        ]
    return Case(
        id='wisp-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive'
        if qualified
        else 'unknown'
        if label.startswith(('unknown', 'unidentified')) or label.endswith('None')
        else 'negative',
        covers=('named:unique:Wisp Projector',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['144:0', '80:0']} if qualified else {})},
            'lines': lines,
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
