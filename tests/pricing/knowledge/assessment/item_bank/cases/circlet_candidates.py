"""Build-specific circlet skill gates; socket/loadout preferences are not minimums."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def specimen(role, quality, guide, variant, label, stats, complete, scenario, sockets=0):
    return Case(
        id=f'circlet-candidate/{role}/{label}',
        item=Item('Diadem', quality, raw_stats=stats, complete=complete, sockets=sockets),
        context={},
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
        report_contains=('Diadem',),
        evidence=(f'pricing/data/wp-a-variants/{guide}.json:/variants/{variant}/player/Helmet',),
    )


def rare_cases():
    for role, klass, guide, variant in (
        ('poison-nova-standard-circlet', 2, 'poison-nova-necromancer', 1),
        ('foh-tribrid-circlet', 3, 'fist-of-the-heavens-paladin', 3),
    ):
        for label, stats, complete, scenario in (
            ('core', ((83, klass, 2), (105, 0, 20)), True, 'positive'),
            ('one-skill-short', ((83, klass, 1), (105, 0, 20)), True, 'negative'),
            ('lower-fcr-affix', ((83, klass, 2), (105, 0, 10)), True, 'negative'),
            ('other-class', ((83, 1, 2), (105, 0, 20)), True, 'negative'),
            ('unread-class', ((105, 0, 20),), False, 'unknown'),
            ('unread-fcr', ((83, klass, 2),), False, 'unknown'),
        ):
            yield specimen(role, 'rare', guide, variant, label, stats, complete, scenario)


def enchant_cases():
    for role, variant in (('enchant-standard-circlet', 1), ('enchant-prebuff-circlet', 3)):
        for label, stats, complete, scenario, sockets in (
            ('fire-three', ((188, 8, 3),), True, 'positive', 0),
            ('two-open-speed', ((188, 8, 3), (96, 0, 30)), True, 'positive', 2),
            ('fire-two', ((188, 8, 2),), True, 'negative', 0),
            ('cold-three', ((188, 10, 3),), True, 'negative', 0),
            ('unread-skill', ((96, 0, 30),), False, 'unknown', 2),
        ):
            yield specimen(role, 'magic', 'enchant-sorceress', variant, label, stats, complete, scenario, sockets)


CASES = (*rare_cases(), *enchant_cases())
