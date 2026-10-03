"""Dwarf Star fixed utility is independent of its variable magic damage reduction."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REASON = 'Gold-find and fire-absorb demand; no separate perfect-MDR premium established.'
FIXED = ((79, 0, 100), (142, 0, 15), (7, 0, 40 * 256), (11, 0, 40 * 256), (28, 0, 15))


def item(mdr):
    raw = (*FIXED, (35, 0, mdr)) if mdr is not None else FIXED
    return Item('Ring', 'unique', 'Dwarf Star', raw, complete=True)


def case(label, captured, status):
    candidate = status == 'candidate'
    return Case(
        id='dwarf-trade/' + label,
        item=captured,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if candidate else 'unknown',
        covers=('named:unique:Dwarf Star',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['35:0']} if candidate else {})},
            'lines': [{'text': 'Trade: ordinary candidate — ' + REASON, 'tone': 'tier_low'}] if candidate else [],
        },
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for mdr in (12, 13, 14, 15):
        yield case(f'mdr-{mdr}', item(mdr), 'candidate')
    for mdr in (None, 11, 16):
        yield case(f'invalid-mdr-{mdr}', item(mdr), 'unresolved')
    for label, changes in (
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield case(label, replace(item(15), **changes), 'unresolved')


CASES = tuple(cases())
