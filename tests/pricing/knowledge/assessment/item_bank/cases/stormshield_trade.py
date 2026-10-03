"""Stormshield underlying demand: native rolls, empty/filled and unknown boundaries."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.caster_stormshield import RAW
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    item = Item('Monarch', 'unique', 'Stormshield', ((31, 0, 133), *RAW), complete=True, named_table_id=253)
    variants = []
    for sockets in (0, 1):
        for defense in (None, 132, 133, 148, 149):
            stats = (*(((31, 0, defense),) if defense is not None else ()), *RAW, *(((194, 0, 1),) if sockets else ()))
            variants.append(
                (f'empty-{sockets}/{defense}', replace(item, sockets=sockets, raw_stats=stats), defense in (133, 148))
            )
    for contents in ('filled', 'unknown', None):
        for defense in (133, 148, 200):
            candidate = observation(
                replace(item, sockets=1, raw_stats=((31, 0, defense), *RAW, (194, 0, 1))), socket_contents=contents
            )
            variants.append((f'insert-{contents}/{defense}', candidate, True))
    for label, changes in [
        ('unidentified', {'identified': False}),
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unknown-sockets', {'sockets': None}),
        ('two-sockets', {'sockets': 2}),
        ('zero-filled', {'socket_contents': 'filled'}),
    ]:
        variants.append((label, observation(item, **changes), False))
    variants.append(('incomplete', replace(item, complete=False), False))
    for stat in (36, 102, 0, 41, 43, 214):
        variants.append(
            (f'missing-{stat}', replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != stat)), False)
        )
    for contents in ('unknown', None):
        variants.append((f'zero-{contents}', observation(item, socket_contents=contents), True))
    for stat, minimum in ((36, 35), (102, 35), (0, 30), (41, 25), (43, 60), (214, 30)):
        for delta in (-1, 1):
            raw = tuple((s, p, minimum + delta if s == stat else v) for s, p, v in item.raw_stats)
            variants.append((f'boundary-{stat}/{delta}', replace(item, raw_stats=raw), delta == 1 and stat != 214))
    for label, candidate, qualifies in variants:
        reason = 'Fixed damage reduction and blocking support Uber setups; ordinary defense still qualifies.'
        if candidate.sockets and candidate.socket_contents != 'empty':
            reason += ' Assess inserts separately.'
        yield Case(
            id='stormshield-trade/' + label,
            item=candidate,
            context={},
            covers=('named:unique:Stormshield',),
            scenario=(
                'positive'
                if qualifies
                else 'unknown'
                if label.startswith(('unknown-', 'missing-'))
                or label in ('incomplete', 'unidentified')
                or label.endswith('/None')
                else 'negative'
            ),
            expected={
                'assessment': IsPartialDict(
                    trade_qualification=IsPartialDict(status='candidate' if qualifies else 'unresolved')
                )
            },
            report_contains=('Trade: candidate',) if qualifies else (),
            report_absent=() if qualifies else ('Trade: candidate',),
            evidence=('pricing/knowledge/assessment/rules/stormshield_trade.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': 'candidate' if qualifies else 'unresolved'},
                'lines': [{'text': 'Trade: candidate — ' + reason, 'tone': 'tier_low'}] if qualifies else [],
            },
        )


CASES = tuple(cases())
