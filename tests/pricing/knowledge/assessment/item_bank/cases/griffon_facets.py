"""Ordinary Lightning Facets remain distinct from Guardian's Thunder setups."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.facet_shields import facet
from tests.pricing.knowledge.assessment.item_bank.cases.griffon_thunder import CHILD as THUNDER
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    ('fist-of-the-heavens-paladin', 2, 'Paladin'),
    ('lightning-sorceress', 3, 'Sorceress'),
    ('lightning-strike-amazon', 2, 'Amazon'),
)


def helmet(child):
    stats = {sid: value for sid, _, value in child.raw_stats}
    return Item(
        'Diadem',
        'unique',
        "Griffon's Eye",
        ((105, 0, 25), (127, 0, 1), (330, 0, 10 + stats.get(330, 0)), (334, 0, 15 + stats.get(334, 0)), (31, 0, 150)),
        sockets=1,
        socket_contents='filled',
        socket_items=(child,),
    )


def cases():
    for build, index, klass in USES:
        role = f'{build}-{index}-griffon-eye'
        config = role + '-stats'
        item = helmet(facet('lightning', 3))
        for label, candidate, payload, scenario in (
            ('minimum-death', item, 'true', 'positive'),
            ('maximum-death', helmet(facet('lightning', 5)), 'true', 'positive'),
            ('minimum-level-up', helmet(facet('lightning', 3, up=True)), 'true', 'positive'),
            ('wrong-element', helmet(facet('fire', 5)), 'false', 'negative'),
            (
                'unnamed-jewel',
                helmet(SocketItem('Jewel', ((330, 0, 5), (334, 0, 5)), complete=True)),
                'false',
                'negative',
            ),
            (
                'different-colossal-option',
                helmet(THUNDER),
                'true' if klass == 'Paladin' else 'false',
                'positive' if klass == 'Paladin' else 'negative',
            ),
            (
                'below-lightning-roll',
                helmet(replace(facet('lightning', 3), raw_stats=((330, 0, 2), (334, 0, 3)))),
                'false',
                'negative',
            ),
            ('unread-child', replace(item, socket_items=()), 'unknown', 'unknown'),
            (
                'partial-child',
                helmet(SocketItem('Jewel', ((330, 0, 3),), name='Rainbow Facet', unique_table_id=392)),
                'unknown',
                'unknown',
            ),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(truth='true'),
                        dependencies=Contains(IsPartialDict(status=payload)),
                    )
                )
            }
            if payload == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('330:0', '334:0')}
                    )
                )
            yield Case(
                id=f'griffon-facet/{build}/{index}/{label}',
                item=candidate,
                context={'player_class': klass},
                scenario=scenario,
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if payload == 'true' else (config,),
                report_contains=("Griffon's Eye", 'Trade tier:', '25% Faster Cast Rate'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{index}',
                    'third-parties/d2data/json/uniqueitems.json:/392',
                    'third-parties/d2data/json/uniqueitems.json:/396',
                ),
            )


CASES = tuple(cases())
