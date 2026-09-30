"""Specialist crafted glove requirements, authored from three cited guide entries."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CONFIGURATIONS = (
    (
        'double-throw-standard-gloves',
        'Vambraces',
        ((93, 0, 20), (81, 0, 1)),
        ((0, 0, 15), (2, 0, 15), (39, 0, 30)),
        'double-throw-barbarian-guide',
        1,
    ),
    (
        'smite-high-investment-gloves',
        'Vampirebone Gloves',
        ((93, 0, 20), (136, 0, 10)),
        ((62, 0, 3), (60, 0, 3), (2, 0, 15), (7, 0, 20 * 256), (41, 0, 30)),
        'smite-paladin',
        2,
    ),
    (
        'dragon-talon-budget-gloves',
        'Vampirebone Gloves',
        ((188, 50, 2), (93, 0, 20), (136, 0, 10), (60, 0, 3)),
        ((7, 0, 20 * 256), (39, 0, 20)),
        'dragon-talon-assassin',
        0,
    ),
)


def cases():
    for role, base, core, secondary, guide, variant in CONFIGURATIONS:
        examples = [
            ('source-rolls', (*core, *secondary), True, False, 'positive'),
            ('core-only', core, True, False, 'positive'),
            ('ethereal', core, True, True, 'negative'),
            ('unread-ethereal', core, True, None, 'unknown'),
            (
                'ten-ias',
                tuple((s, layer, 10 if s == 93 else value) for s, layer, value in core),
                True,
                False,
                'negative',
            ),
        ]
        if role == 'dragon-talon-budget-gloves':
            examples.extend(
                (
                    ('one-martial-skill', ((188, 50, 1), *core[1:]), True, False, 'negative'),
                    ('trap-not-martial', ((188, 48, 2), *core[1:]), True, False, 'negative'),
                    ('mana-not-life-steal', (*core[:-1], (62, 0, 3)), True, False, 'negative'),
                )
            )
        for stat, layer, _ in core:
            remaining = tuple(row for row in core if row[:2] != (stat, layer))
            examples.extend(
                (
                    (f'missing-{stat}-{layer}', remaining, True, False, 'negative'),
                    (f'unread-{stat}-{layer}', remaining, False, False, 'unknown'),
                )
            )
        for label, stats, complete, ethereal, scenario in examples:
            truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
            yield Case(
                id=f'crafted-glove-candidate/{role}/{label}',
                item=Item(base, 'crafted', raw_stats=stats, complete=complete, ethereal=ethereal),
                context={},
                scenario=scenario,
                covers=(role,),
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
                    )
                },
                report_contains=(base,),
                evidence=(f'pricing/data/wp-a-variants/{guide}.json:/variants/{variant}/player/Gloves',),
            )


CASES = tuple(cases())
