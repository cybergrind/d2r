"""Original fixed IK belts: small component demand, separate from upgraded variants."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    original = Item(
        'War Belt', 'set', "Immortal King's Detail", ((31, 0, 89), (0, 0, 25), (39, 0, 28), (41, 0, 31)), complete=True
    )
    variants = [('original', original, True)]
    variants += [
        (
            'upgraded',
            replace(original, base='Colossus Girdle', raw_stats=((31, 0, 107), *original.raw_stats[1:])),
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
    for label, candidate, qualifies in variants:
        status = 'candidate' if qualifies else 'unresolved'
        yield Case(
            id='ik-detail-trade/' + label,
            item=candidate,
            context={},
            covers=("named:set:Immortal King's Detail",),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            report_contains=('Trade tier: low', 'Low-value IK component with fixed bonuses') if qualifies else (),
            report_absent=() if qualifies else ('Trade: candidate',),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [
                    {
                        'text': 'Trade: candidate — Low-value IK component with fixed bonuses. '
                        'Set bonuses need other set pieces.',
                        'tone': 'tier_low',
                    }
                ]
                if qualifies
                else [],
            },
        )


CASES = tuple(cases())
