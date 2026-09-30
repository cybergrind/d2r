"""Source-authored 3/20 magic and 2/20 rare Amazon glove boundaries."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


MAGIC_ROLES = ('lightning-fury-standard-gloves', 'lightning-strike-boss-gloves')
RARE_ROLES = ('lightning-fury-mf-gloves', 'lightning-fury-ubers-gloves', 'lightning-strike-standard-gloves')
STRIKE_SOURCE = 'pricing/data/wp-a-variants/lightning-strike-amazon.json:/variants/1/player/Gloves'


def cases():
    for quality, skill, roles, variants in (
        ('magic', 3, MAGIC_ROLES, (1,)),
        ('rare', 2, RARE_ROLES, (2, 3)),
    ):
        core = ((188, 2, skill), (93, 0, 20))
        examples = (
            ('core', core, True, False, 'positive'),
            ('one-skill-short', ((188, 2, skill - 1), (93, 0, 20)), True, False, 'negative'),
            ('ten-ias', ((188, 2, skill), (93, 0, 10)), True, False, 'negative'),
            ('wrong-tab', ((188, 0, skill), (93, 0, 20)), True, False, 'negative'),
            ('missing-skills', ((93, 0, 20),), True, False, 'negative'),
            ('unread-skills', ((93, 0, 20),), False, False, 'unknown'),
            ('missing-ias', ((188, 2, skill),), True, False, 'negative'),
            ('unread-ias', ((188, 2, skill),), False, False, 'unknown'),
            ('ethereal', core, True, True, 'negative'),
            ('unread-ethereal', core, True, None, 'unknown'),
        )
        evidence = (
            STRIKE_SOURCE,
            *(
                f'pricing/data/wp-a-variants/lightning-fury-amazon-guide.json:/variants/{v}/player/Gloves'
                for v in variants
            ),
        )
        for label, stats, complete, ethereal, scenario in examples:
            truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
            yield Case(
                id=f'javelin-glove-candidate/{quality}/{label}',
                item=Item('Chain Gloves', quality, raw_stats=stats, complete=complete, ethereal=ethereal),
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
                report_contains=('Chain Gloves',),
                evidence=evidence,
            )

    for label, context, truth, scenario in (
        ('arachnid-equipped', {'player_items': ['Arachnid Mesh']}, 'true', 'positive'),
        ('wrong-belt', {'player_items': ['Razortail']}, 'false', 'negative'),
        ('unread-belt', {}, 'unknown', 'unknown'),
    ):
        yield Case(
            id='javelin-glove-candidate/boss-swap/' + label,
            item=Item('Chain Gloves', 'magic', raw_stats=((188, 2, 3), (93, 0, 20)), complete=True),
            context=context,
            scenario=scenario,
            covers=('lightning-strike-boss-gloves',),
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(
                        IsPartialDict(
                            id='lightning-strike-boss-gloves',
                            rule_trace=IsPartialDict(truth='true'),
                            dependencies=Contains(
                                IsPartialDict(label='Arachnid Mesh for the cited boss glove swap', status=truth)
                            ),
                        )
                    )
                )
            },
            report_contains=('Chain Gloves',),
            evidence=(STRIKE_SOURCE,),
        )


CASES = tuple(cases())
