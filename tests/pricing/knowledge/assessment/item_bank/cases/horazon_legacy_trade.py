"""Horazon boots: ordinary demand with complete, unmodified native roll evidence."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Mirrored Boots', 'set', "Horazon's Legacy", ((31, 0, 68), (0, 0, 15), (2, 0, 15), (37, 0, 30)), complete=True
)
KEYS = ['31:0', '0:0', '2:0', '37:0']


def make_case(label, item, qualified):
    status = 'candidate' if qualified else 'unresolved'
    defense = next((v for s, p, v in item.raw_stats if s == 31 and p == 0), None)
    return Case(
        id=f'horazon-legacy-trade/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario=(
            'positive'
            if qualified
            else 'unknown'
            if label.startswith('unknown-') or label in ('unidentified', 'incomplete') or label.endswith('-None')
            else 'negative'
        ),
        covers=(f'named:set:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': KEYS} if qualified else {})},
            'lines': [
                {
                    'text': 'Trade: ordinary candidate — Cannot Be Frozen boots with ordinary set-item demand.',
                    'tone': 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=(f'Defense: {defense} (59-68)',) if qualified else (),
        report_absent=('Trade: use only', 'Trade: premium candidate'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for defense, strength, dex, resist in product((59, 68), (10, 15), (10, 15), (20, 30)):
        raw = ((31, 0, defense), (0, 0, strength), (2, 0, dex), (37, 0, resist))
        yield make_case(f'{defense}-{strength}-{dex}-{resist}', replace(ITEM, raw_stats=raw), True)
    for stat, values in ((31, (None, 58, 69, 368)), (0, (None, 9, 16)), (2, (None, 9, 16, 35)), (37, (None, 19, 31))):
        for value in values:
            raw = tuple(
                (s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None
            )
            yield make_case(f'stat-{stat}-{value}', replace(ITEM, raw_stats=raw), False)
    for stat in (16, 214, 215):
        yield make_case(f'extra-{stat}', replace(ITEM, raw_stats=(*ITEM.raw_stats, (stat, 0, 1))), False)
    yield make_case('conditional-walk', replace(ITEM, raw_stats=(*ITEM.raw_stats, (96, 0, 40))), True)
    for label, changes in (
        ('incomplete', {'complete': False}),
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(ITEM, **changes), False)


CASES = tuple(cases())
