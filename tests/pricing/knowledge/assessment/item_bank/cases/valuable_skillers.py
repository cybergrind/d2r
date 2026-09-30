"""Plain and premium skillers stay useful below planner-perfect life rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Authored from the cited guide charm cells, not inferred from runtime predicates.
SPECS = (
    ('lightning', 'Sorceress', 9, None, ('lightning-starter-skiller',)),
    ('poison', 'Necromancer', 17, None, ('poison-starter-skiller',)),
    ('lightning-life', 'Sorceress', 9, 7, ('lightning-standard-life-skiller', 'nova-standard-life-skiller')),
    ('poison-life', 'Necromancer', 17, 7, ('poison-standard-life-skiller',)),
    ('javelin-life', 'Amazon', 2, 7, ('fury-standard-life-skiller',)),
    ('combat-life', 'Paladin', 24, 7, ('hammer-standard-life-skiller',)),
    ('lightning-recovery', 'Sorceress', 9, 99, ('lightning-standard-fhr-skiller',)),
    ('combat-recovery', 'Paladin', 24, 99, ('hammer-standard-fhr-skiller',)),
)


def cases():
    for slug, player_class, tab, suffix, roles in SPECS:
        skill = (188, tab, 1)
        stats = (skill,) + (((suffix, 0, 37 * 256 if suffix == 7 else 12),) if suffix else ())
        item = Item('Grand Charm', 'magic', raw_stats=stats, complete=True)
        configs = tuple(role + '-stats' for role in roles)
        rows = [('useful-roll', item, 'true')]
        if suffix == 7:
            rows.extend(
                (
                    ('lowest-life-affix', replace(item, raw_stats=(skill, (7, 0, 5 * 256))), 'true'),
                    ('perfect-life', replace(item, raw_stats=(skill, (7, 0, 45 * 256))), 'true'),
                )
            )
        for stat, parameter, _ in stats:
            remaining = tuple(row for row in stats if row[:2] != (stat, parameter))
            rows.extend(
                (
                    (f'missing-{stat}', replace(item, raw_stats=remaining), 'false'),
                    (f'unread-{stat}', replace(item, raw_stats=remaining, complete=False), 'unknown'),
                )
            )
        rows.extend(
            (
                ('wrong-tree', replace(item, raw_stats=((188, 10, 1), *stats[1:])), 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), 'unknown'),
            )
        )
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
                id=f'valuable-skillers/{slug}/{label}',
                item=candidate,
                context={'player_class': player_class},
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Grand Charm',),
                evidence=(
                    'pricing/data/wp-a-builds.json',
                    'third-parties/d2data/json/magicprefix.json',
                    'third-parties/d2data/json/magicsuffix.json',
                ),
            )


CASES = tuple(cases())
