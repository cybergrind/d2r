"""Native-decoded Guardian's Thunder identity and known minimum lightning rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLES = (
    ('fist-of-the-heavens-paladin', 2, 'Paladin'),
    ('lightning-fury-amazon-guide', 1, 'Amazon'),
    ('lightning-fury-amazon-guide', 3, 'Amazon'),
    ('nova-sorceress-guide', 2, 'Sorceress'),
    ('lightning-strike-amazon', 1, 'Amazon'),
    ('lightning-sentry-assassin', 1, 'Assassin'),
    ('lightning-sorceress', 1, 'Sorceress'),
    ('lightning-sorceress', 2, 'Sorceress'),
    ('nova-sorceress-guide', 1, 'Sorceress'),
    ('nova-sorceress-guide', 3, 'Sorceress'),
    ('lightning-fury-amazon-guide', 2, 'Amazon'),
)
# Socket stats require a complete linked-child capture. The parent remains partial
# and cannot receive a complete-item price.
CHILD = SocketItem(
    'Colossal Jewel',
    ((330, 0, 5), (334, 0, 5), (50, 0, 1), (51, 0, 75), (85, 0, 3), (80, 0, 15), (79, 0, 25), (201, 235 * 64 + 25, 1)),
    complete=True,
    name="Guardian's Thunder",
    unique_table_id=421,
)
ITEM = Item(
    'Diadem',
    'unique',
    "Griffon's Eye",
    ((105, 0, 25), (127, 0, 1), (330, 0, 15), (334, 0, 20), (31, 0, 150)),
    sockets=1,
    socket_contents='filled',
    socket_items=(CHILD,),
)


def cases():
    examples = (
        ('minimum-known-lightning', ITEM, 'true', 'true', 'positive'),
        (
            'perfect-lightning',
            replace(
                ITEM,
                raw_stats=tuple(
                    (sid, layer, value + 5 if sid in (330, 334) else value) for sid, layer, value in ITEM.raw_stats
                ),
                socket_items=(
                    replace(
                        CHILD,
                        raw_stats=tuple(
                            (sid, layer, 10 if sid in (330, 334) else value) for sid, layer, value in CHILD.raw_stats
                        ),
                    ),
                ),
            ),
            'true',
            'true',
            'positive',
        ),
        (
            'below-damage',
            replace(
                ITEM,
                socket_items=(
                    replace(
                        CHILD,
                        raw_stats=tuple(
                            (sid, layer, 4 if sid == 330 else value) for sid, layer, value in CHILD.raw_stats
                        ),
                    ),
                ),
            ),
            'true',
            'false',
            'negative',
        ),
        (
            'below-pierce',
            replace(
                ITEM,
                socket_items=(
                    replace(
                        CHILD,
                        raw_stats=tuple(
                            (sid, layer, 4 if sid == 334 else value) for sid, layer, value in CHILD.raw_stats
                        ),
                    ),
                ),
            ),
            'true',
            'false',
            'negative',
        ),
        ('unknown-ethereal', replace(ITEM, ethereal=None), 'unknown', 'true', 'unknown'),
        (
            'ordinary-jewel-same-lightning',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((330, 0, 5), (334, 0, 5))),)),
            'true',
            'false',
            'negative',
        ),
        (
            'missing-pierce',
            replace(ITEM, socket_items=(replace(CHILD, raw_stats=((330, 0, 5),), complete=False),)),
            'true',
            'unknown',
            'unknown',
        ),
        ('unread-child', replace(ITEM, socket_items=()), 'true', 'unknown', 'unknown'),
        ('ethereal-player-helmet', replace(ITEM, ethereal=True), 'false', 'true', 'negative'),
    )
    for build, variant, klass in ROLES:
        role = f'{build}-{variant}-griffon-eye'
        config = role + '-stats'
        for label, item, required, payload, scenario in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(truth=required),
                        dependencies=Contains(IsPartialDict(status=payload)),
                    )
                ),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('330:0', '334:0')}
                    )
                )
            yield Case(
                id=f'griffon-thunder/{build}/{variant}/{label}',
                item=item,
                context={'player_class': klass},
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (config,),
                report_contains=("Griffon's Eye", 'Trade tier:'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                    'third-parties/d2data/json/uniqueitems.json:/421',
                ),
            )


CASES = tuple(cases())
