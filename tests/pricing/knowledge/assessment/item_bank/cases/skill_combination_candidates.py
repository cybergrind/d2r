"""Magic claws and prebuff orbs: skill candidates are separate from a full guide setup."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('lightning-sentry-claw-candidate', 'lightning-sentry-assassin', 271, 262, 'Lightning Sentry'),
    ('wake-of-fire-claw-candidate', 'wake-of-fire-assassin', 262, 271, 'Wake of Fire'),
)


def cases():
    for role, guide, skill, other, skill_name in SPECS:
        for label, stats, complete, scenario in (
            ('guide-core', ((188, 48, 3), (107, skill, 3), (93, 0, 40)), True, 'positive'),
            ('modest-candidate', ((188, 48, 1), (107, skill, 1)), True, 'positive'),
            ('other-trap', ((188, 48, 3), (107, other, 3), (93, 0, 40)), True, 'negative'),
            ('no-trap-tab', ((107, skill, 3), (93, 0, 40)), True, 'negative'),
            ('unread-trap-tab', ((107, skill, 3), (93, 0, 40)), False, 'unknown'),
            ('unread-staffmod', ((188, 48, 3), (93, 0, 40)), False, 'unknown'),
        ):
            yield Case(
                id=f'trap-claw-candidate/{guide}/{label}',
                item=Item('Greater Talons', 'magic', raw_stats=stats, complete=complete),
                context={'player_class': 'Assassin'},
                scenario=scenario,
                covers=(role,),
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(
                            IsPartialDict(
                                id=role,
                                rule_trace=IsPartialDict(
                                    truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                                ),
                            )
                        )
                    )
                },
                report_contains=('Greater Talons', skill_name) if scenario == 'positive' else ('Greater Talons',),
                evidence=(
                    f'pricing/data/wp-a-variants/{guide}.json:/variants/1/player/Weapon',
                    'third-parties/d2data/json/skills.json',
                ),
            )


CASES = tuple(cases())


def prebuff_cases():
    role = 'enchant-prebuff-orb-candidate'
    skills = ((188, 8, 3), (107, 52, 3), (107, 61, 3))
    examples = [
        ('guide-core', skills, True, 'positive'),
        ('modest-candidate', tuple((stat, layer, 1) for stat, layer, _ in skills), True, 'positive'),
    ]
    for index, component in enumerate(('fire-tab', 'enchant', 'mastery')):
        remaining = skills[:index] + skills[index + 1 :]
        examples.extend(
            (
                (f'missing-{component}', remaining, True, 'negative'),
                (f'unread-{component}', remaining, False, 'unknown'),
            )
        )
    for label, stats, complete, scenario in examples:
        yield Case(
            id='prebuff-orb-candidate/' + label,
            item=Item('Eldritch Orb', 'magic', raw_stats=stats, complete=complete),
            context={'player_class': 'Sorceress'},
            scenario=scenario,
            covers=(role,),
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(
                                truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                            ),
                        )
                    )
                )
            },
            report_contains=('Eldritch Orb', 'Enchant', 'Fire Mastery')
            if scenario == 'positive'
            else ('Eldritch Orb',),
            evidence=(
                'pricing/data/wp-a-variants/enchant-sorceress.json:/variants/3/player/Weapon',
                'third-parties/d2data/json/skills.json',
            ),
        )


CASES += tuple(prebuff_cases())
