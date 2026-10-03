"""Mara shared-roll trade segments and native component integrity."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


KEYS = (39, 41, 43, 45)
ITEM = Item('Amulet', 'unique', "Mara's Kaleidoscope", tuple((key, 0, 30) for key in KEYS))


def cases():
    for value in (19, 20, 26, 27, 28, 29, 30, 31):
        status = 'premium' if value == 30 else 'candidate' if 27 <= value <= 29 else 'unresolved'
        yield make_case(f'res-{value}', replace(ITEM, raw_stats=tuple((key, 0, value) for key in KEYS)), status)
    for key in KEYS:
        yield make_case(
            f'missing-{key}', replace(ITEM, raw_stats=tuple(r for r in ITEM.raw_stats if r[0] != key)), 'unresolved'
        )
        yield make_case(
            f'unequal-{key}',
            replace(ITEM, raw_stats=tuple((s, p, 29 if s == key else v) for s, p, v in ITEM.raw_stats)),
            'unresolved',
        )
    for label, specimen in (
        ('unidentified', replace(ITEM, identified=False)),
        ('ethereal', replace(ITEM, ethereal=True)),
        ('unknown-ethereal', replace(ITEM, ethereal=None)),
        ('socketed', replace(ITEM, sockets=1)),
        ('unknown-sockets', replace(ITEM, sockets=None)),
        ('unknown-contents', replace(ITEM, socket_contents='unknown')),
    ):
        yield make_case(label, specimen, 'unresolved')


def make_case(label, specimen, status):
    qualified = status != 'unresolved'
    reason = (
        '30 all resistances: perfect shared-roll premium candidate.'
        if status == 'premium'
        else '27-29 all resistances: ordinary trade candidate; premium requires 30.'
    )
    text = 'Trade: ' + ('premium' if status == 'premium' else 'ordinary') + ' candidate — ' + reason
    return Case(
        id='mara-trade/' + label,
        item=specimen,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive'
        if qualified
        else 'unknown'
        if label.startswith(('missing', 'unknown', 'unidentified'))
        else 'negative',
        covers=("named:unique:Mara's Kaleidoscope",),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': ['39:0', '41:0', '43:0', '45:0']} if qualified else {}),
            },
            'lines': [{'text': text, 'tone': 'tier_high' if status == 'premium' else 'tier_low'}] if qualified else [],
        },
        report_contains=('Trade tier: mid',) if status == 'candidate' else (),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
