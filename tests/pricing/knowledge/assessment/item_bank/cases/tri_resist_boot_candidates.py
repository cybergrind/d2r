"""Shared rare-boot candidate boundaries across eight explicitly cited setups."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = (
    'blizzard-standard-boots',
    'lightning-sentry-standard-boots',
    'fire-warlock-standard-boots',
    'fire-warlock-mf-boots',
    'lightning-fury-ubers-boots',
    'lightning-strike-ubers-boots',
    'fissure-ubers-boots',
    'lightning-sorceress-ubers-boots',
)
SOURCES = tuple(
    f'pricing/data/wp-a-variants/{guide}.json:/variants/{variant}/player/Boots'
    for guide, variant in (
        ('blizzard-sorceress', 1),
        ('lightning-sentry-assassin', 1),
        ('fire-warlock-guide', 1),
        ('fire-warlock-guide', 2),
        ('lightning-fury-amazon-guide', 3),
        ('lightning-strike-amazon', 2),
        ('fissure-druid', 3),
        ('lightning-sorceress', 3),
    )
)
CORE = ((96, 0, 30), (39, 0, 40), (41, 0, 40), (43, 0, 40))


def cases():
    examples = [
        ('shared-core', 'Heavy Boots', CORE, True, False, 'positive'),
        ('ubers-recovery-dexterity', 'Light Plated Boots', (*CORE, (99, 0, 10), (2, 0, 9)), True, False, 'positive'),
        ('mf-recovery', 'Scarabshell Boots', (*CORE, (99, 0, 10), (80, 0, 25)), True, False, 'positive'),
        ('poison-duration-recovery', 'Heavy Boots', (*CORE, (99, 0, 10), (110, 0, 25)), True, False, 'positive'),
        ('modest-resists', 'Heavy Boots', ((96, 0, 10), (39, 0, 5), (41, 0, 5), (43, 0, 5)), True, False, 'positive'),
        ('ethereal', 'Heavy Boots', CORE, True, True, 'negative'),
        ('unread-ethereal', 'Heavy Boots', CORE, True, None, 'unknown'),
        ('poison-instead-of-cold', 'Heavy Boots', (*CORE[:-1], (45, 0, 40)), True, False, 'negative'),
    ]
    for stat, label in ((96, 'movement'), (39, 'fire'), (41, 'lightning'), (43, 'cold')):
        remaining = tuple(row for row in CORE if row[0] != stat)
        examples.extend(
            (
                (f'missing-{label}', 'Heavy Boots', remaining, True, False, 'negative'),
                (f'unread-{label}', 'Heavy Boots', remaining, False, False, 'unknown'),
            )
        )
    for label, base, stats, complete, ethereal, scenario in examples:
        truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
        yield Case(
            id='tri-resist-boot-candidate/' + label,
            item=Item(base, 'rare', raw_stats=stats, complete=complete, ethereal=ethereal),
            context={},
            scenario=scenario,
            covers=ROLES,
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(*[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES])
                )
            },
            report_contains=(base,),
            evidence=SOURCES,
        )


CASES = tuple(cases())
