"""Arachnid's verified perfect-ED segment, separate from its caster usefulness."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FIXED = ((105, 0, 20), (127, 0, 1), (77, 0, 5), (150, 0, 10))
ITEM = Item('Spiderweb Sash', 'unique', 'Arachnid Mesh', (*FIXED, (16, 0, 120)), named_table_id=373)
REASON = '120% enhanced defense: perfect-roll premium asking segment.'


def make_case(label, specimen, status, tier=None):
    return Case(
        id='arachnid-trade/' + label,
        item=specimen,
        context={},
        expected={
            'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status)),
            'price_estimate': IsPartialDict(estimate_ist=None),
        },
        scenario='positive' if status == 'premium' else 'unknown',
        covers=('named:unique:Arachnid Mesh',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['16:0']} if status == 'premium' else {})},
            'lines': [{'text': 'Trade: premium candidate — ' + REASON, 'tone': 'tier_high'}]
            if status == 'premium'
            else [],
        },
        report_contains=(f'Trade tier: {tier}',) if tier else (),
        report_absent=('Trade: use only',),
        evidence=('pricing/data/appraisal-arachnid-trade-review-2026-10-02.md',),
    )


def cases():
    for ed in (90, 109, 110, 119, 120):
        yield make_case(
            f'ed-{ed}',
            replace(ITEM, raw_stats=(*FIXED, (16, 0, ed))),
            'premium' if ed == 120 else 'unresolved',
            'high' if ed == 120 else 'mid',
        )
    for ed in (None, 89, 121):
        yield make_case(
            f'invalid-{ed}', replace(ITEM, raw_stats=FIXED if ed is None else (*FIXED, (16, 0, ed))), 'unresolved'
        )
    for label, changes in (
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unidentified', {'identified': False}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
        ('filled', {'socket_contents': 'filled'}),
    ):
        yield make_case(label, replace(ITEM, **changes), 'unresolved')


CASES = tuple(cases())
