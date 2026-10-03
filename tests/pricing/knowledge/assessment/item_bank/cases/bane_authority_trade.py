"""Original fixed caster belt asks do not establish upgraded or premium demand."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


REASON = 'Low-value original belt with fixed 10% faster cast rate and 20 life; no variable-roll premium.'


def cases():
    original = Item('Light Belt', 'set', "Bane's Authority", ((31, 0, 3), (105, 0, 10), (7, 0, 5120)), complete=True)
    variants = [
        ('original', original, True),
        ('partial-set-energy', replace(original, raw_stats=(*original.raw_stats, (1, 0, 15))), True),
        (
            'exceptional',
            replace(original, base='Sharkskin Belt', raw_stats=((31, 0, 36), *original.raw_stats[1:])),
            False,
        ),
        ('elite', replace(original, base='Vampirefang Belt', raw_stats=((31, 0, 61), *original.raw_stats[1:])), False),
        ('ethereal', replace(original, ethereal=True), False),
        ('unknown-ethereal', observation(original, ethereal=None), False),
        ('unknown-sockets', observation(original, sockets=None), False),
        ('unknown-contents', observation(original, socket_contents='unknown'), False),
        ('unidentified', replace(original, identified=False), False),
        ('socketed', replace(original, sockets=1), False),
        ('missing-fixed-bonuses', replace(original, raw_stats=((31, 0, 3),)), False),
    ]
    for label, cast, life in [('cast-low', 9, 20), ('cast-high', 11, 20), ('life-low', 10, 19), ('life-high', 10, 21)]:
        variants.append((label, replace(original, raw_stats=((31, 0, 3), (105, 0, cast), (7, 0, life * 256))), False))
    for label, item, qualifies in variants:
        status = 'candidate' if qualifies else 'unresolved'
        yield Case(
            id='bane-authority-trade/' + label,
            item=item,
            context={},
            covers=("named:set:Bane's Authority",),
            scenario='positive' if qualifies else 'unknown' if label.startswith('unknown') else 'negative',
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            report_contains=('Trade tier: low', REASON) if qualifies else (),
            report_absent=('Trade: premium',) if qualifies else ('Trade: ordinary candidate', 'Trade: premium'),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [{'text': 'Trade: ordinary candidate — ' + REASON, 'tone': 'tier_low'}] if qualifies else [],
            },
        )


CASES = tuple(cases())
