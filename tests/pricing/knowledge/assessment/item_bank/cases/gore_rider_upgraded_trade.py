"""Upgraded perfect ED retains a separately rolled base; no max-defense premium."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_trade import boots
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case


def upgraded(ed=200, base_defense=62):
    original = boots(ed)
    return replace(
        original,
        base='Myrmidon Greaves',
        raw_stats=((31, 0, base_defense * (100 + ed) // 100), *original.raw_stats[1:]),
    )


def cases():
    variants = [(f'ed200-base-{base}', upgraded(base_defense=base), True) for base in range(62, 72)]
    variants += [(f'ed{ed}-base-{base}', upgraded(ed, base), False) for ed in (160, 196, 199) for base in (62, 71)]
    variants += [(f'invalid-ed-{ed}', upgraded(ed), False) for ed in (159, 201)]
    original = upgraded()
    variants += [
        (
            'unknown-ed',
            replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != 16), complete=False),
            False,
        ),
        ('ethereal', replace(original, ethereal=True), False),
        ('unknown-ethereal', observation(original, ethereal=None), False),
        ('unknown-sockets', observation(original, sockets=None), False),
        ('unknown-contents', observation(original, socket_contents='unknown'), False),
        ('filled', observation(original, socket_contents='filled'), False),
        ('unidentified', replace(original, identified=False), False),
        ('socketed', replace(original, sockets=1), False),
    ]
    reason = '200% enhanced defense on upgraded boots; base defense can still vary.'
    for label, candidate, qualifies in variants:
        status = 'candidate' if qualifies else 'unresolved'
        yield Case(
            id='gore-rider-upgraded-trade/' + label,
            item=candidate,
            context={},
            covers=('named:unique:Gore Rider',),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={
                'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status)),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
            report_contains=(reason,) if qualifies else (),
            report_absent=('low defense still has trade interest.',)
            + (() if qualifies else ('Trade: ordinary candidate',)),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if qualifies else [],
            },
        )


CASES = tuple(cases())
