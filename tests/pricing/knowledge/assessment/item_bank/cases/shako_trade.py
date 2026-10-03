"""Ordinary Shako trade demand is independent of class and high defense rolls."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RAW = (
    (127, 0, 2),
    (80, 0, 50),
    (36, 0, 10),
    (216, 0, 12 * 256),
    (217, 0, 12 * 256),
    (0, 0, 2),
    (1, 0, 2),
    (2, 0, 2),
    (3, 0, 2),
)


def cases():
    item = Item('Shako', 'unique', 'Harlequin Crest', ((31, 0, 98), *RAW), complete=True)
    variants = [
        ('minimum', item, True),
        ('maximum', replace(item, raw_stats=((31, 0, 141), *RAW)), True),
        ('ethereal', replace(item, ethereal=True, raw_stats=((31, 0, 147), *RAW)), False),
        ('unknown-ethereal', observation(item, ethereal=None), False),
        ('incomplete', replace(item, complete=False), False),
        ('illegal-defense', replace(item, raw_stats=((31, 0, 142), *RAW)), False),
        ('two-sockets', replace(item, sockets=2, raw_stats=(*item.raw_stats, (194, 0, 2))), False),
        ('one-empty', replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))), True),
        (
            'filled',
            observation(replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))), socket_contents='filled'),
            True,
        ),
        (
            'unknown-contents',
            observation(replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))), socket_contents='unknown'),
            True,
        ),
    ]
    for sockets in (0, 1):
        for defense in (None, 97, 98, 141, 142):
            raw = (*(((31, 0, defense),) if defense is not None else ()), *RAW, *(((194, 0, 1),) if sockets else ()))
            candidate = replace(item, sockets=sockets, raw_stats=raw)
            variants.append(
                (f'empty-{sockets}/defense-{defense}', candidate, defense is not None and 98 <= defense <= 141)
            )
    for contents in ('filled', 'unknown', None):
        for defense in (98, 141, 180):
            candidate = observation(
                replace(item, sockets=1, raw_stats=((31, 0, defense), *RAW, (194, 0, 1))), socket_contents=contents
            )
            variants.append((f'insert-{contents}/defense-{defense}', candidate, True))
    for label, changes, qualifies in [
        ('unidentified', {'identified': False}, False),
        ('ethereal-bad-defense', {'ethereal': True}, False),
        ('unknown-sockets', {'sockets': None}, False),
        ('zero-unknown', {'socket_contents': 'unknown'}, True),
        ('zero-null', {'socket_contents': None}, True),
        ('zero-filled', {'socket_contents': 'filled'}, False),
    ]:
        variants.append((label, observation(item, **changes), qualifies))
    for label, candidate, qualifies in variants:
        reason = 'Useful fixed skills, life/mana and magic find; low defense still qualifies.'
        if candidate.socket_contents != 'empty' and candidate.sockets:
            reason += ' Assess inserts separately.'
        yield Case(
            id='shako-trade/' + label,
            item=candidate,
            context={},
            covers=('named:unique:Harlequin Crest',),
            scenario='positive'
            if qualifies
            else 'unknown'
            if label in ('incomplete', 'unknown-ethereal')
            else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status='candidate'))}
            if qualifies
            else {},
            report_contains=('Trade: candidate', 'low defense still qualifies') if qualifies else (),
            report_absent=() if qualifies else ('Trade: candidate',),
            evidence=('pricing/knowledge/assessment/rules/shako_trade.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': 'candidate' if qualifies else 'unresolved'},
                'lines': [{'text': 'Trade: candidate — ' + reason, 'tone': 'tier_med'}] if qualifies else [],
            },
        )


CASES = tuple(cases())
