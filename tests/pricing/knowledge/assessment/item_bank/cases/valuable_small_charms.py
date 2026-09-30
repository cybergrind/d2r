"""Independently authored charm combinations from Standard, MF and Ubers cells."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RESISTS = tuple((stat, 0, 5) for stat in (39, 41, 43, 45))
SPECS = (
    ('lightning-mf', 'Sorceress', ((80, 0, 7), *RESISTS), ('lightning-standard-sc-mf-res', 'lightning-mf-sc-mf-res')),
    (
        'lightning-fhr',
        'Sorceress',
        ((99, 0, 5), *RESISTS),
        ('lightning-standard-sc-fhr-res', 'lightning-mf-sc-fhr-res'),
    ),
    ('lightning-ubers', 'Sorceress', ((7, 0, 20 * 256), *RESISTS), ('lightning-ubers-sc-life-res',)),
    (
        'nova-light-mf',
        'Sorceress',
        ((41, 0, 11), (80, 0, 7)),
        ('nova-standard-sc-light-mf', 'nova-mf-sc-light-mf', 'nova-hydra-sc-light-mf'),
    ),
    (
        'nova-mf',
        'Sorceress',
        ((80, 0, 7), *RESISTS),
        ('nova-standard-sc-mf-res', 'nova-mf-sc-mf-res', 'nova-hydra-sc-mf-res'),
    ),
    ('nova-mana-mf', 'Sorceress', ((9, 0, 17 * 256), (80, 0, 7)), ('nova-mf-sc-mana-mf',)),
    ('nova-fire-mf', 'Sorceress', ((39, 0, 11), (80, 0, 7)), ('nova-hydra-sc-fire-mf',)),
    ('hammer-mf', 'Paladin', ((80, 0, 7), *RESISTS), ('hammer-standard-sc-mf-res', 'hammer-mf-sc-mf-res')),
    ('hammer-ubers', 'Paladin', ((7, 0, 20 * 256), *RESISTS), ('hammer-ubers-sc-life-res',)),
    ('poison-mf', 'Necromancer', ((80, 0, 7), *RESISTS), ('poison-standard-sc-mf-res', 'poison-mf-sc-mf-res')),
    ('poison-fhr', 'Necromancer', ((99, 0, 5), *RESISTS), ('poison-standard-sc-fhr-res',)),
)


def cases():
    for slug, player_class, stats, roles in SPECS:
        item = Item('Small Charm', 'magic', raw_stats=stats, complete=True)
        configs = tuple(role + '-stats' for role in roles)
        lower = tuple(
            (stat, layer, 5 * 256 if stat in (7, 9) else 3 if stat != 99 else value) for stat, layer, value in stats
        )
        rows = [('guide-example', item, 'true'), ('lower-legal-rolls', replace(item, raw_stats=lower), 'true')]
        for stat, layer, _ in stats:
            remaining = tuple(row for row in stats if row[:2] != (stat, layer))
            rows.extend(
                (
                    (f'missing-{stat}', replace(item, raw_stats=remaining), 'false'),
                    (f'unread-{stat}', replace(item, raw_stats=remaining, complete=False), 'unknown'),
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
                            f'{stat}:{layer}': IsPartialDict(configuration_ids=Contains(*configs))
                            for stat, layer, _ in stats
                        }
                    )
                )
            yield Case(
                id=f'valuable-small-charms/{slug}/{label}',
                item=candidate,
                context={'player_class': player_class},
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Small Charm',),
                evidence=(
                    'pricing/data/wp-a-builds.json',
                    'third-parties/d2data/json/magicprefix.json',
                    'third-parties/d2data/json/magicsuffix.json',
                ),
            )


CASES = tuple(cases())
