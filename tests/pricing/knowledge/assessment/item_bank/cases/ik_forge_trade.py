"""Small trades for fixed IK gloves stay separate from owning a partial set."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def glove(defense, *, partial=False):
    return Item(
        'War Gauntlets',
        'set',
        "Immortal King's Forge",
        ((31, 0, defense), (0, 0, 20), (2, 0, 20), (201, (38 << 6) | 4, 12), *(((93, 0, 25),) if partial else ())),
        complete=True,
    )


def cases():
    original = glove(108)
    variants = [(f'defense-{d}', glove(d), True) for d in (108, 111, 118)]
    variants += [(f'partial-defense-{d}', glove(d, partial=True), True) for d in (228, 238)]
    variants += [
        ('upgraded', replace(original, base='Ogre Gauntlets'), False),
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
            id='ik-forge-trade/' + label,
            item=candidate,
            context={},
            covers=("named:set:Immortal King's Forge",),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            report_contains=('Trade tier: low', 'Low-value IK component', 'other set pieces') if qualifies else (),
            report_absent=() if qualifies else ('Trade: candidate',),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [
                    {
                        'text': 'Trade: candidate — Low-value IK component; defense has no established premium. '
                        'Set bonuses need other set pieces.',
                        'tone': 'tier_low',
                    }
                ]
                if qualifies
                else [],
            },
        )


CASES = tuple(cases())
