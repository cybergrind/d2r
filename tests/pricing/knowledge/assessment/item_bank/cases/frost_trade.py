"""Reviewed cold-socket demand without an unsupported perfect-roll premium."""

from dataclasses import replace
from itertools import product

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.elemental_colossal_recipients import jewel
from tests.pricing.knowledge.assessment.item_bank.models import Case


AXES = ((331, 5, 10), (335, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50))
REASON = 'Cold socket damage/pierce and farming utility; no separate perfect-roll premium established.'


def item(values):
    original = jewel('cold')
    replace_stats = dict(zip((s for s, _, _ in AXES), values, strict=True))
    raw = tuple(
        (s, p, replace_stats.get(s, v))
        for s, p, v in original.raw_stats
        if s not in replace_stats or replace_stats[s] is not None
    )
    return replace(original, raw_stats=raw)


def case(label, captured, status):
    candidate = status == 'candidate'
    return Case(
        id='frost-trade/' + label,
        item=captured,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario=(
            'positive'
            if candidate
            else 'unknown'
            if label.startswith('unknown-') or label in ('unidentified', 'incomplete') or label.endswith('-None')
            else 'negative'
        ),
        covers=("named:unique:Protector's Frost",),
        trade_checks={
            'schema_version': 1,
            'qualification': {
                'status': status,
                **({'material_stats': [f'{s}:0' for s, _, _ in AXES]} if candidate else {}),
            },
            'lines': [{'text': 'Trade: ordinary candidate — ' + REASON, 'tone': 'tier_low'}] if candidate else [],
        },
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for values in product(*((lo, hi) for _, lo, hi in AXES)):
        yield case('rolls-' + '-'.join(map(str, values)), item(values), 'candidate')
    for values in ((8, 9, 3, 27, 47), (9, 8, 4, 34, 42), (10, 10, 5, 32, 45)):
        yield case('observed-' + '-'.join(map(str, values)), item(values), 'candidate')
    maximum = tuple(hi for _, _, hi in AXES)
    for index, (stat, lo, hi) in enumerate(AXES):
        for value in (None, lo - 1, hi + 1):
            values = list(maximum)
            values[index] = value
            yield case(f'invalid-{stat}-{value}', item(values), 'unresolved')
    for label, changes in (
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('socketed', {'sockets': 1}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
    ):
        yield case(label, replace(item(maximum), **changes), 'unresolved')


CASES = tuple(cases())
