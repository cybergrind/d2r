"""Class-correct Torch utility across explicitly enumerated build inventories."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.torch_caster_tables import ATTRIBUTES, RESISTS, torch
from tests.pricing.knowledge.assessment.item_bank.models import Case


USES = (
    (
        'Amazon',
        0,
        (('lightning-fury-amazon-guide', (1, 2, 3)), ('lightning-strike-amazon', (1, 2)), ('strafe-amazon', (1, 2))),
    ),
    (
        'Sorceress',
        1,
        (
            ('meteor-sorceress', (1, 2, 3, 4)),
            ('lightning-sorceress', (1, 2, 3)),
            ('enchant-sorceress', (1, 2, 3)),
            ('nova-sorceress-guide', (1, 2, 3)),
        ),
    ),
    ('Necromancer', 2, (('poison-nova-necromancer', (1, 2, 5)), ('summoner-necromancer-guide', (1, 2)))),
    (
        'Paladin',
        3,
        (('dream-paladin', (0, 1, 2)), ('fist-of-the-heavens-paladin', (2, 3, 4)), ('smite-paladin', (1, 2))),
    ),
    ('Barbarian', 4, (('double-throw-barbarian-guide', (1, 2)), ('gold-find-barbarian', (1, 2, 3, 4)))),
    ('Druid', 5, (('fissure-druid', (1, 2)),)),
    (
        'Assassin',
        6,
        (
            ('dragon-talon-assassin', (0, 1)),
            ('fire-blast-assassin', (1, 2)),
            ('lightning-sentry-assassin', (1, 2)),
            ('wake-of-fire-assassin', (1, 3)),
        ),
    ),
    (
        'Warlock',
        7,
        (
            ('echoing-strike-warlock-guide', (1, 2, 3)),
            ('fire-warlock-guide', (1, 2)),
            ('mirrored-blades-warlock-guide', (1, 2)),
        ),
    ),
)


def cases():
    for player_class, layer, uses in USES:
        roles = tuple(f'{g}-{i}-torch' for g, indices in uses for i in indices)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        item = torch(layer)
        other = 3 if layer != 3 else 1
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', torch(layer, 20, 20), context, 'true'),
            ('attributes-perfect', torch(layer, 20, 10), context, 'true'),
            ('resistance-perfect', torch(layer, 10, 20), context, 'true'),
            ('wrong-torch', torch(other), context, 'false'),
            ('two-classes', replace(item, raw_stats=(*item.raw_stats, (83, other, 3))), context, 'false'),
            ('skill-too-low', torch(layer, skill=2), context, 'false'),
            ('skill-too-high', torch(layer, skill=4), context, 'false'),
            ('unknown-skill', replace(item, raw_stats=item.raw_stats[1:], complete=False), context, 'unknown'),
            ('unknown-wearer', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-sockets', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in (f'83:{layer}', *(f'{s}:0' for s in (*ATTRIBUTES, *RESISTS)))
                        }
                    )
                )
            yield Case(
                id=f'torch-variants/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else configs,
                absent_stat_configurations=dict.fromkeys(('89:0', '198:12618', '204:3998'), configs),
                report_contains=('Hellfire Torch', 'Trade tier:') if truth == 'true' else ('Large Charm',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/400',
                    *(('pricing/raw/mr/planners/rg2je0ld.json:/data',) if player_class == 'Warlock' else ()),
                    *(
                        f'pricing/data/wp-a-builds.json:/{g}/variants/{i}/player/Charms'
                        for g, indices in uses
                        for i in indices
                    ),
                ),
            )


CASES = tuple(cases())
