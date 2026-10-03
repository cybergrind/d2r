"""Torch class choice is independent of shared attribute/resistance rolls."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_unique_charms import TORCH_FIXED
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLL_KEYS = (0, 1, 2, 3, 39, 41, 43, 45)
REASON = 'Amazon Torch: ordinary trade candidate; no separate premium roll segment established.'


def torch(class_id, attributes, resists):
    rolls = tuple((stat, 0, attributes if stat < 4 else resists) for stat in ROLL_KEYS)
    return Item('Large Charm', 'unique', 'Hellfire Torch', ((83, class_id, 3), *rolls, *TORCH_FIXED), complete=True)


def case(label, item, status):
    candidate = status == 'candidate'
    return Case(
        id='torch-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if candidate else 'unknown',
        covers=('named:unique:Hellfire Torch',),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': [f'{s}:0' for s in ROLL_KEYS]} if candidate else {}),
            },
            'lines': [{'text': 'Trade: ordinary candidate — ' + REASON, 'tone': 'tier_low'}] if candidate else [],
        },
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for class_id, attributes, resists in product(range(8), (10, 20), (10, 20)):
        yield case(
            f'class-{class_id}/{attributes}-{resists}',
            torch(class_id, attributes, resists),
            'candidate' if class_id == 0 else 'unresolved',
        )
    for attributes, resists in ((15, 11), (20, 14), (18, 19)):
        yield case(f'observed/{attributes}-{resists}', torch(0, attributes, resists), 'candidate')
    maximum = torch(0, 20, 20)
    for stat in ROLL_KEYS:
        for value in (None, 9, 10, 21):
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in maximum.raw_stats if s != stat or value is not None
            )
            yield case(f'stat-{stat}-{value}', replace(maximum, raw_stats=raw), 'unresolved')
    for label, changes in (
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
        ('incomplete-capture', {'complete': False}),
    ):
        yield case(label, replace(maximum, **changes), 'unresolved')
    for label, raw in (
        ('missing-class', maximum.raw_stats[1:]),
        ('multiple-classes', (*maximum.raw_stats, (83, 1, 3))),
        ('duplicate-class', (*maximum.raw_stats, (83, 0, 3))),
        ('invalid-class', ((83, 8, 3), *maximum.raw_stats[1:])),
        ('low-bonus', ((83, 0, 2), *maximum.raw_stats[1:])),
        ('high-bonus', ((83, 0, 4), *maximum.raw_stats[1:])),
    ):
        yield case(label, replace(maximum, raw_stats=raw), 'unresolved')


CASES = tuple(cases())
