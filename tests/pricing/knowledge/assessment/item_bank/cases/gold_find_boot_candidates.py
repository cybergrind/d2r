"""Gold farmer boot combinations: budget specialist use is not generic leveling."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'gold-find-budget-boots'
CORE = ((96, 0, 20), (39, 0, 35), (79, 0, 70))
SOURCE = 'pricing/data/wp-a-variants/gold-find-barbarian.json:/variants/0/player/Boots'


def cases():
    examples = [
        ('source-rolls', (*CORE, (99, 0, 10)), True, False, 'positive'),
        ('core-only', CORE, True, False, 'positive'),
        ('ethereal', CORE, True, True, 'negative'),
        ('unread-ethereal', CORE, True, None, 'unknown'),
        ('magic-find-not-gold', (*CORE[:-1], (80, 0, 25)), True, False, 'negative'),
        ('cold-not-fire', (CORE[0], CORE[2], (43, 0, 35)), True, False, 'negative'),
    ]
    for stat, label in ((96, 'movement'), (39, 'fire-resist'), (79, 'gold-find')):
        remaining = tuple(row for row in CORE if row[0] != stat)
        examples.extend(
            (
                (f'missing-{label}', remaining, True, False, 'negative'),
                (f'unread-{label}', remaining, False, False, 'unknown'),
            )
        )
    for label, stats, complete, ethereal, scenario in examples:
        truth = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
        yield Case(
            id='gold-find-boot-candidate/' + label,
            item=Item('Heavy Boots', 'rare', raw_stats=stats, complete=complete, ethereal=ethereal),
            context={},
            scenario=scenario,
            covers=(ROLE,),
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))
                )
            },
            report_contains=('Heavy Boots',),
            evidence=(SOURCE,),
        )


CASES = tuple(cases())
