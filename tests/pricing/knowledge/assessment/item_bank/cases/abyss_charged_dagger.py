"""Passive Warlock skills survive depleted charges; Lower Resist is not magic pierce."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'abyss-warlock-build-guide-skill-charge-combination'


def cases():
    for rarity in ('magic', 'rare'):
        for remaining in (0, 1):
            item = Item('Kriss', rarity, raw_stats=((83, 7, 2), (204, 91 * 64 + 3, (82 << 8) | remaining)))
            for ethereal in (False, True):
                annotations = {'83:7': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))}
                if remaining:
                    annotations['204:5827'] = IsPartialDict(
                        desirability='supporting', configuration_ids=Contains(ROLE + '-stats')
                    )
                yield Case(
                    id=f'abyss/charged-dagger/{rarity}/{remaining}/{ethereal}',
                    item=replace(item, ethereal=ethereal),
                    context={'player_class': 'Warlock'},
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth='true'))),
                            stat_evaluation=IsPartialDict(annotations=IsPartialDict(annotations)),
                        )
                    },
                    covers=(ROLE,),
                    scenario='positive',
                    absent_stat_configurations={} if remaining else {'204:5827': (ROLE + '-stats',)},
                    evidence=(
                        'third-parties/d2data/json/skills.json:/91',
                        'pricing/data/appraisal-guide-sections.json',
                    ),
                )

    for label, raw, complete, truth in (
        ('missing-prefix', ((204, 5827, (82 << 8) | 1),), True, 'false'),
        ('wrong-charge', ((83, 7, 2), (204, 5572, (35 << 8) | 1)), True, 'false'),
        ('unread-charge', ((83, 7, 2),), False, 'unknown'),
    ):
        yield Case(
            id=f'abyss/charged-dagger/{label}',
            item=Item('Kriss', 'magic', raw_stats=raw, complete=complete),
            context={'player_class': 'Warlock'},
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))
                )
            },
            covers=(ROLE,),
            scenario='negative' if truth == 'false' else 'unknown',
            absent_configurations=(ROLE + '-stats',),
            evidence=('third-parties/d2data/json/skills.json:/91',),
        )


CASES = tuple(cases())
