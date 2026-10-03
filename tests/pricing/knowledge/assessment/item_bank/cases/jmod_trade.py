"""Fixed JMOD affixes establish a trade base independently of defense and class."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    raw = ((20, 0, 42), (102, 0, 30), (31, 0, 133), (194, 0, 4))
    item = Item('Monarch', 'magic', raw_stats=raw, sockets=4, complete=True)
    variants = [
        ('minimum-defense', item, {}, True),
        ('maximum-defense', replace(item, raw_stats=tuple((s, p, 148 if s == 31 else v) for s, p, v in raw)), {}, True),
        ('unrelated-player-class', item, {'player_class': 'Warlock'}, True),
        ('unknown-contents', observation(item, socket_contents='unknown'), {}, True),
        ('filled-unread-payload', observation(item, socket_contents='filled'), {}, True),
        ('ethereal', replace(item, ethereal=True), {}, False),
        ('unknown-ethereal', observation(item, ethereal=None), {}, False),
        ('unidentified', replace(item, identified=False), {}, False),
        ('three-sockets', replace(item, sockets=3, raw_stats=(*raw[:-1], (194, 0, 3))), {}, False),
        ('low-block', replace(item, raw_stats=((20, 0, 41), *raw[1:])), {}, False),
        ('bonus-mistaken-for-total', replace(item, raw_stats=((20, 0, 20), *raw[1:])), {}, False),
        ('incomplete', replace(item, complete=False), {}, False),
        (
            'socket-boosted-fbr',
            replace(item, raw_stats=tuple((s, p, 50 if s == 102 else v) for s, p, v in raw)),
            {},
            False,
        ),
        ('rare', replace(item, rarity='rare'), {}, False),
    ]
    for label, candidate, context, qualifies in variants:
        reason = 'JMOD base for endgame facet shields.'
        if label == 'filled-unread-payload':
            reason += ' The shield remains useful after clearing sockets; assess the inserts separately.'
        elif label == 'unknown-contents':
            reason += ' Check the socket contents separately.'
        yield Case(
            id='jmod-trade/' + label,
            item=candidate,
            context=context,
            covers=('trade:magic:jmod-shell',),
            scenario='positive'
            if qualifies
            else 'unknown'
            if label in ('unknown-ethereal', 'incomplete', 'unidentified')
            else 'negative',
            expected={
                'assessment': IsPartialDict(
                    trade_qualification=IsPartialDict(
                        status='candidate', assessment_scope='recoverable_shell', material_stats=[]
                    )
                )
            }
            if qualifies
            else {},
            report_contains=('Trade: candidate', 'JMOD base') if qualifies else (),
            report_absent=() if qualifies else ('JMOD base for endgame facet shields.',),
            evidence=('pricing/knowledge/assessment/rules/magic_trade.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': 'candidate' if qualifies else None},
                'lines': [{'text': 'Trade: candidate — ' + reason, 'tone': 'tier_low'}] if qualifies else [],
            },
        )


CASES = tuple(cases())
