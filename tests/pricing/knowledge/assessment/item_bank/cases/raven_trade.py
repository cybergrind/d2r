"""Joint dexterity/attack-rating trade boundaries, independent of build roles."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Ring', 'unique', 'Raven Frost', ((2, 0, 20), (19, 0, 250)))
ORDINARY = 'Ordinary roll; premium requires 20 dexterity and 250 attack rating.'
PREMIUM = '20 dexterity and 250 attack rating: double-perfect premium asking segment.'


def cases():
    for dexterity, rating in product((15, 16, 19, 20), (150, 151, 249, 250)):
        status = 'premium' if (dexterity, rating) == (20, 250) else 'candidate'
        yield make_case(
            f'dex-{dexterity}-ar-{rating}', replace(ITEM, raw_stats=((2, 0, dexterity), (19, 0, rating))), status
        )
    for key, values in ((2, (14, 21, None)), (19, (149, 251, None))):
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
        id='raven-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive'
        if qualified
        else 'unknown'
        if label.startswith(('unknown', 'unidentified')) or label.endswith('None')
        else 'negative',
        covers=('named:unique:Raven Frost',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['2:0', '19:0']} if qualified else {})},
            'lines': lines,
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
