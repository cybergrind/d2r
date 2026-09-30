"""Guide charm combinations require each observed component, not planner-perfect rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RESISTS = tuple((stat, 0, 5) for stat in (39, 41, 43, 45))
SPECS = (
    ('life-all-res', 'Small Charm', ((7, 0, 20 * 256), *RESISTS), ('blizzard-standard-sc-life-res',)),
    ('life-cold', 'Small Charm', ((7, 0, 20 * 256), (43, 0, 11)), ('blizzard-standard-sc-life-cold',)),
    ('mf-all-res', 'Small Charm', ((80, 0, 7), *RESISTS), ('blizzard-mf-sc-mf-res', 'blizzard-set-sc-mf-res')),
    ('fhr-all-res', 'Small Charm', ((99, 0, 5), *RESISTS), ('blizzard-mf-sc-fhr-res', 'blizzard-set-sc-fhr-res')),
    ('cold-life-skiller', 'Grand Charm', ((188, 10, 1), (7, 0, 45 * 256)), ('blizzard-standard-life-skiller',)),
)


def cases():
    for slug, base, stats, roles in SPECS:
        item = Item(base, 'magic', raw_stats=stats, complete=True)
        configs = tuple(role + '-stats' for role in roles)
        lower = tuple(
            (stat, parameter, 5 * 256 if stat == 7 else 3 if stat in (39, 41, 43, 45, 80) else value)
            for stat, parameter, value in stats
        )
        rows = [('guide-example', item, 'true'), ('lower-legal-rolls', replace(item, raw_stats=lower), 'true')]
        for stat, parameter, _ in stats:
            remaining = tuple(row for row in stats if row[:2] != (stat, parameter))
            rows.extend(
                (
                    (f'missing-{stat}-{parameter}', replace(item, raw_stats=remaining), 'false'),
                    (f'unread-{stat}-{parameter}', replace(item, raw_stats=remaining, complete=False), 'unknown'),
                )
            )
        if slug == 'cold-life-skiller':
            rows.append(('wrong-skill-tab', replace(item, raw_stats=((188, 9, 1), (7, 0, 45 * 256))), 'false'))
        for label, candidate, truth in rows:
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{stat}:{parameter}': IsPartialDict(configuration_ids=Contains(*configs))
                            for stat, parameter, _ in stats
                        }
                    )
                )
            yield Case(
                id=f'blizzard/magic-charms/{slug}/{label}',
                item=candidate,
                context={'player_class': 'Sorceress'},
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(base,),
                evidence=(
                    'pricing/data/wp-a-builds.json:/blizzard-sorceress/variants',
                    'third-parties/d2data/json/magicprefix.json',
                    'third-parties/d2data/json/magicsuffix.json',
                ),
            )


CASES = tuple(cases())
