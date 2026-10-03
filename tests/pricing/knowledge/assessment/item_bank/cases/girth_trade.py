"""Girth total defense, decoded mana and set contribution boundaries."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item('Troll Belt', 'set', "Trang-Oul's Girth", ((31, 0, 166), (9, 0, 50 * 256)), complete=True)


def cases():
    for total, mana in product((134, 159, 166), (25, 49, 50)):
        yield make_case(
            f'roll-{total}-{mana}',
            replace(ITEM, raw_stats=((31, 0, total), (9, 0, mana * 256))),
            'premium' if mana == 50 else 'candidate',
        )
    for key, values in ((31, (None, 100, 133, 167, 366)), (9, (None, 24 * 256, 51 * 256, 150 * 256))):
        for value in values:
            raw = tuple((s, p, value if s == key else v) for s, p, v in ITEM.raw_stats if s != key or value is not None)
            yield make_case(f'component-{key}-{value}', replace(ITEM, raw_stats=raw), 'unresolved')
    yield make_case('fractional-mana', replace(ITEM, raw_stats=((31, 0, 166), (9, 0, 50 * 256 - 1))), 'unresolved')
    for stat in (16, 214, 215):
        yield make_case(f'extra-defense-{stat}', replace(ITEM, raw_stats=(*ITEM.raw_stats, (stat, 0, 1))), 'unresolved')
    yield make_case('conditional-cold', replace(ITEM, raw_stats=(*ITEM.raw_stats, (43, 0, 40))), 'premium')
    for label, changes in (
        ('incomplete', {'complete': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unidentified', {'identified': False}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield make_case(label, replace(ITEM, **changes), 'unresolved')


def make_case(label, specimen, status):
    qualified = status != 'unresolved'
    premium = status == 'premium'
    reason = '50 mana: higher-demand roll.' if premium else 'Mana below 50: ordinary trade candidate.'
    total = next((r[2] for r in specimen.raw_stats if r[0] == 31), None)
    return Case(
        id='girth-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=("named:set:Trang-Oul's Girth",),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['31:0', '9:0']} if qualified else {})},
            'lines': [
                {
                    'text': 'Trade: ' + ('premium' if premium else 'ordinary') + ' candidate — ' + reason,
                    'tone': 'tier_high' if premium else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_contains=(('Trade tier: mid' if premium else 'Trade tier: low'), f'Defense: {total} (134-166)')
        if qualified
        else (),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
