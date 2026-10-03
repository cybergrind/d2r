"""Annihilus independent shared rolls, asking segments and native rejection cases."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ATTRIBUTES = (0, 1, 2, 3)
RESISTANCES = (39, 41, 43, 45)
MATERIAL = (*ATTRIBUTES, *RESISTANCES, 85)


def item(attributes=20, resistance=20, experience=10):
    return Item(
        'Small Charm',
        'unique',
        'Annihilus',
        (
            (127, 0, 1),
            *((s, 0, attributes) for s in ATTRIBUTES),
            *((s, 0, resistance) for s in RESISTANCES),
            (85, 0, experience),
        ),
    )


def make_case(label, specimen, status, reason=None):
    qualified = status != 'unresolved'
    return Case(
        id='annihilus-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=('named:unique:Annihilus',),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': [f'{s}:0' for s in MATERIAL]} if qualified else {}),
            },
            'lines': [
                {
                    'text': 'Trade: ' + ('premium' if status == 'premium' else 'ordinary') + ' candidate — ' + reason,
                    'tone': 'tier_high' if status == 'premium' else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=('Trade tier: high' if status == 'premium' else 'Trade tier: low',) if qualified else (),
        report_absent=('Trade: use only',)
        + (('Trade tier: high', 'Trade: premium candidate') if not qualified else ()),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for attributes, resistance, experience in product((10, 18, 19, 20), (10, 18, 19, 20), (5, 9, 10)):
        high = min(attributes, resistance) >= 19
        reason = (
            '19+ attributes and resistances: higher asking segment.'
            if high
            else 'Ordinary Annihilus; higher asking demand requires both attributes and resistances at 19+.'
        )
        yield make_case(
            f'roll-{attributes}-{resistance}-{experience}',
            item(attributes, resistance, experience),
            'premium' if high else 'candidate',
            reason,
        )
    perfect = item()
    complete = make_case(
        'complete-perfect-thin-price',
        replace(perfect, complete=True),
        'premium',
        '19+ attributes and resistances: higher asking segment.',
    )
    yield replace(
        complete,
        expected={
            **complete.expected,
            'price_estimate': IsPartialDict(
                estimate_ist=None, basis='unavailable', unavailable_reason='thin', sellers=2
            ),
        },
    )
    for stat in MATERIAL:
        minimum, maximum = (5, 10) if stat == 85 else (10, 20)
        for value in (None, minimum - 1, maximum + 1):
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in perfect.raw_stats if s != stat or value is not None
            )
            yield make_case(f'component-{stat}-{value}', replace(perfect, raw_stats=raw), 'unresolved')
    for stat in (*ATTRIBUTES, *RESISTANCES):
        for value in (10, 19):
            raw = tuple((s, p, value if s == stat else v) for s, p, v in perfect.raw_stats)
            yield make_case(f'unequal-{stat}-{value}', replace(perfect, raw_stats=raw), 'unresolved')
    for label, changes in (
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unidentified', {'identified': False}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(perfect, **changes), 'unresolved')


CASES = tuple(cases())
