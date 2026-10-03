"""Maximum MF can support ordinary demand without a perfect-roll premium."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Ring', 'unique', 'Nagelring', ((80, 0, 30), (19, 0, 75)))


def cases():
    for mf, ar in product((15, 29, 30), (50, 74, 75)):
        yield make_case(
            f'roll-{mf}-{ar}',
            replace(ITEM, raw_stats=((80, 0, mf), (19, 0, ar))),
            'candidate' if mf == 30 else 'unresolved',
        )
    for key, lo, hi in ((80, 15, 30), (19, 50, 75)):
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
    qualified = status == 'candidate'
    return Case(
        id='nagel-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Nagelring',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['80:0', '19:0']} if qualified else {})},
            'lines': [
                {
                    'text': (
                        'Trade: ordinary candidate — 30% magic find: ordinary low-tier trade candidate; '
                        'no verified perfect-AR premium.'
                    ),
                    'tone': 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=('Trade tier: low',) if qualified else (),
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
