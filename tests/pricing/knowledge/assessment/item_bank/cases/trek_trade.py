"""Ethereal Trek attribute thresholds do not turn secondary rolls into premiums."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FIXED = ((96, 0, 20), (99, 0, 20), (154, 0, 50), (242, 0, 8), (252, 0, 5))
MATERIAL = ['0:0', '3:0', '16:0', '45:0']


def specimen(strength=15, vitality=15, defense=170, poison=70):
    return Item(
        'Scarabshell Boots',
        'unique',
        'Sandstorm Trek',
        (
            *FIXED,
            (0, 0, strength),
            (3, 0, vitality),
            (16, 0, defense),
            (45, 0, poison),
            (31, 0, 99 * (100 + defense) // 100),
        ),
        ethereal=True,
        complete=True,
        named_table_id=369,
    )


def make_case(label, item, status):
    qualified = status != 'unresolved'
    reason = (
        'Ethereal with 15 Strength and 15 Vitality: premium attribute-roll candidate.'
        if status == 'premium'
        else 'Ethereal roll: ordinary trade candidate; premium attribute segment requires 15 Strength and 15 Vitality.'
    )
    kind = 'premium candidate' if status == 'premium' else 'ordinary candidate'
    return Case(
        id='trek-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Sandstorm Trek',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': MATERIAL} if qualified else {})},
            'lines': [{'text': f'Trade: {kind} — {reason}', 'tone': 'tier_high' if status == 'premium' else 'tier_low'}]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for strength, vitality, defense, poison in product((10, 14, 15), (10, 14, 15), (140, 170), (40, 70)):
        item = specimen(strength, vitality, defense, poison)
        yield make_case(
            f'{strength}-{vitality}-{defense}-{poison}', item, 'premium' if strength == vitality == 15 else 'candidate'
        )
    base = specimen()
    for stat, low, high in ((0, 10, 15), (3, 10, 15), (16, 140, 170), (45, 40, 70)):
        for value in (None, low - 1, high + 1):
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in base.raw_stats if s != stat or value is not None
            )
            yield make_case(f'component-{stat}-{value}', replace(base, raw_stats=raw), 'unresolved')
    for label, changes in (
        ('nonethereal', {'ethereal': False}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unidentified', {'identified': False}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        item = replace(base, **changes)
        if label == 'nonethereal':
            item = replace(item, raw_stats=tuple((s, p, 178 if s == 31 else v) for s, p, v in item.raw_stats))
        yield make_case(label, item, 'unresolved')


CASES = tuple(cases())
