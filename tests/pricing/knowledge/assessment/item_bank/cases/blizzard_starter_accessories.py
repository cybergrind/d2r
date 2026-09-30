"""Starter guide accessories: observed combinations and partial capture boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('amulet', Item('Amulet', 'magic', raw_stats=((188, 10, 1), (105, 0, 10)), complete=True), ((188, 10), (105, 0))),
    ('belt', Item('Demonhide Sash', 'magic', raw_stats=((99, 0, 24), (39, 0, 30)), complete=True), ((99, 0), (39, 0))),
    (
        'ring',
        Item(
            'Ring',
            'rare',
            'Storm Circle',
            ((0, 0, 10), (7, 0, 20 * 256), (43, 0, 20), (138, 0, 1), (80, 0, 10)),
            complete=True,
        ),
        ((0, 0), (7, 0), (43, 0)),
    ),
)


def cases():
    for slug, item, required in SPECS:
        role = 'blizzard-starter-' + slug
        config = role + '-stats'
        rows = [('guide-example', item, 'true')]
        for key in required:
            stats = tuple(row for row in item.raw_stats if row[:2] != key)
            rows.extend(
                (
                    (f'absent-{key}', replace(item, raw_stats=stats), 'false'),
                    (f'unread-{key}', replace(item, raw_stats=stats, complete=False), 'unknown'),
                )
            )
        if slug == 'amulet':
            rows.extend(
                (
                    ('wrong-tab', replace(item, raw_stats=((188, 9, 1), (105, 0, 10))), 'false'),
                    ('below-fcr', replace(item, raw_stats=((188, 10, 1), (105, 0, 9))), 'false'),
                    ('three-skills', replace(item, raw_stats=((188, 10, 3), (105, 0, 10))), 'true'),
                )
            )
        if slug == 'ring':
            rows.append(('core-without-mf-maek', replace(item, raw_stats=item.raw_stats[:3]), 'true'))
        for label, candidate, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{s}:{p}': IsPartialDict(configuration_ids=Contains(config))
                            for s, p, _ in candidate.raw_stats
                        }
                    )
                )
            yield Case(
                id=f'blizzard/starter-accessories/{slug}/{label}',
                item=candidate,
                context={'player_class': 'Sorceress'},
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=(candidate.base,),
                evidence=('pricing/data/wp-a-builds.json:/blizzard-sorceress/variants/0/player',),
            )


CASES = tuple(cases())
