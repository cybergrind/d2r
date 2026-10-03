"""Titan trade qualification: paired ED, leech, ethereal and native/upgraded bases."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FIXED = ((83, 0, 2), (188, 2, 2), (96, 0, 30), (253, 0, 30), (0, 0, 20), (2, 0, 20), (254, 0, 60))


def specimen(base, ed=200, leech=9):
    # Trade material and guaranteed utility properties; damage totals are not
    # fabricated. This is an explicitly partial capture with all trade axes known.
    return Item(
        base,
        'unique',
        "Titan's Revenge",
        (*FIXED, (17, 0, ed), (18, 0, ed), (60, 0, leech)),
        ethereal=True,
        named_table_id=281,
    )


def cases():
    for base in ('Ceremonial Javelin', 'Matriarchal Javelin'):
        threshold = 190 if base == 'Ceremonial Javelin' else 200
        for ed, leech in product((150, 189, 190, 191, 199, 200), (5, 9)):
            item = specimen(base, ed, leech)
            yield make_case(f'{base}/ed-{ed}-leech-{leech}', item, 'premium' if ed >= threshold else 'unresolved')
        item = specimen(base)
        for label, changes in (
            ('nonethereal', {'ethereal': False}),
            ('unknown-ethereal', {'ethereal': None}),
            ('unidentified', {'identified': False}),
            ('impossible-socket', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
        ):
            yield make_case(base + '/' + label, replace(item, **changes), 'unresolved')
        for stat, low, high in ((17, 150, 200), (18, 150, 200), (60, 5, 9)):
            for value in (None, low - 1, high + 1):
                raw = tuple(
                    (s, p, value if s == stat else v) for s, p, v in item.raw_stats if s != stat or value is not None
                )
                yield make_case(f'{base}/component-{stat}-{value}', replace(item, raw_stats=raw), 'unresolved')
        raw = tuple((s, p, 199 if s == 18 else v) for s, p, v in item.raw_stats)
        yield make_case(base + '/mismatched-ed', replace(item, raw_stats=raw), 'unresolved')
        raw = tuple((s, p, 199 if s == 17 else v) for s, p, v in item.raw_stats)
        yield make_case(base + '/reverse-mismatched-ed', replace(item, raw_stats=raw), 'unresolved')
        for ed in (149, 201):
            yield make_case(f'{base}/shared-invalid-{ed}', specimen(base, ed), 'unresolved')


def make_case(label, item, status):
    premium = status == 'premium'
    original = item.base == 'Ceremonial Javelin'
    segment = 'original base with 190%+' if original else 'upgraded base with 200%'
    reason = f'Ethereal {segment} enhanced damage: premium asking segment; life leech remains relevant to price.'
    return Case(
        id='titan-trade/' + label,
        item=item,
        context={},
        expected={
            'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status)),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        scenario='positive'
        if premium
        else 'unknown'
        if label.startswith('missing') or label == 'unidentified'
        else 'negative',
        covers=("named:unique:Titan's Revenge",),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['17:0', '18:0', '60:0']} if premium else {})},
            'lines': [{'text': f'Trade: premium candidate — {reason}', 'tone': 'tier_high'}] if premium else [],
        },
        report_contains=(
            *(("Titan's Revenge", reason) if premium else ()),
            *((('Trade tier: high' if premium else 'Trade tier: mid'),) if '/ed-' in label else ()),
        ),
        report_absent=() if premium else ('Trade: premium candidate', 'Trade: ordinary candidate', 'Trade: use only'),
        evidence=(
            'pricing/data/wp-i-uniques-misc.json:/UQ-titan-s-revenge',
            'pricing/knowledge/assessment/rules/named_tiers.json',
        ),
    )


CASES = tuple(cases())
