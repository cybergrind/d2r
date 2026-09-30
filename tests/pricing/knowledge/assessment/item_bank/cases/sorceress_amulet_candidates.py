"""Independent Nova, Enchant caster and Fire prebuff amulet boundaries."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    (
        'nova',
        'crafted',
        (83, 1, 2),
        10,
        ('nova-standard-amulet', 'nova-mf-amulet', 'nova-hydra-amulet'),
        'nova-sorceress-guide',
        (1, 2, 3),
    ),
    (
        'enchant',
        'crafted',
        (83, 1, 2),
        15,
        ('enchant-standard-amulet', 'enchant-mf-amulet'),
        'enchant-sorceress',
        (1, 2),
    ),
    (
        'prebuff',
        'magic',
        (188, 8, 3),
        10,
        ('enchant-prebuff-amulet', 'enchant-budget-amulet'),
        'enchant-sorceress',
        (0, 3),
    ),
)


def cases():
    for group, quality, skill, fcr, roles, guide, variants in GROUPS:
        stat, layer, amount = skill
        core = (skill, (105, 0, fcr))
        examples = (
            ('source-core', core, True, 'positive'),
            ('one-skill-short', ((stat, layer, amount - 1), (105, 0, fcr)), True, 'negative'),
            ('slow-cast', (skill, (105, 0, 10 if fcr == 15 else 5)), True, 'negative'),
            ('wrong-skill', ((stat, 2 if stat == 83 else 9, amount), (105, 0, fcr)), True, 'negative'),
            ('missing-skill', ((105, 0, fcr),), True, 'negative'),
            ('unread-skill', ((105, 0, fcr),), False, 'unknown'),
            ('missing-fcr', (skill,), True, 'negative'),
            ('unread-fcr', (skill,), False, 'unknown'),
        )
        for label, stats, complete, scenario in examples:
            truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
            yield Case(
                id=f'sorceress-amulet-candidate/{group}/{label}',
                item=Item('Amulet', quality, raw_stats=stats, complete=complete),
                context={},
                scenario=scenario,
                covers=roles,
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            *[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles]
                        )
                    )
                },
                report_contains=('Amulet',),
                evidence=tuple(
                    f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}/player/Amulet' for variant in variants
                ),
            )


def lightning_cases():
    role = 'lightning-starter-amulet'
    for label, stats, complete, scenario in (
        ('three-lightning', ((188, 9, 3),), True, 'positive'),
        ('three-lightning-fcr', ((188, 9, 3), (105, 0, 10)), True, 'positive'),
        ('two-lightning', ((188, 9, 2),), True, 'negative'),
        ('three-fire', ((188, 8, 3),), True, 'negative'),
        ('two-class-skills', ((83, 1, 2),), True, 'negative'),
        ('absent', (), True, 'negative'),
        ('unread', (), False, 'unknown'),
    ):
        truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
        yield Case(
            id='sorceress-amulet-candidate/lightning/' + label,
            item=Item('Amulet', 'magic', raw_stats=stats, complete=complete),
            context={},
            scenario=scenario,
            covers=(role,),
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
                )
            },
            report_contains=('Amulet',),
            evidence=('pricing/data/wp-a-builds.json:/lightning-sorceress/variants/0/player/Amulet',),
        )


CASES = (*cases(), *lightning_cases())
