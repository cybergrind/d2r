"""Bul-Kathos trade segments through native capture and report generation."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Ring', 'unique', "Bul-Kathos' Wedding Band", ((60, 0, 5),))
ORDINARY = '3\u20134% life leech: ordinary trade candidate; premium requires 5%.'
PREMIUM = '5% life leech: perfect-roll premium asking segment.'


def cases():
    for leech in (2, 3, 4, 5, 6):
        status = 'premium' if leech == 5 else 'candidate' if leech in (3, 4) else 'unresolved'
        yield make_case(f'leech-{leech}', replace(ITEM, raw_stats=((60, 0, leech),)), status)
    for label, item in (
        ('missing-leech', replace(ITEM, raw_stats=())),
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
        id='bk-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive'
        if qualified
        else 'unknown'
        if label.startswith(('unknown', 'missing', 'unidentified'))
        else 'negative',
        covers=("named:unique:Bul-Kathos' Wedding Band",),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['60:0']} if qualified else {})},
            'lines': lines,
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
