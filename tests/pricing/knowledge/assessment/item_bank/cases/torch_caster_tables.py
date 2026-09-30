"""Caster Torch support requires exactly the wearer class; effects are not passive damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Warlock', 7, (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        1,
        (
            ('fire-wall-sorceress-guide', 30),
            ('frozen-orb-meteor-sorceress', 29),
            ('hydra-sorceress', 29),
            ('frozen-orb-sorceress', 29),
        ),
    ),
)
ATTRIBUTES = (0, 1, 2, 3)
RESISTS = (39, 41, 43, 45)
FIXED = ((89, 0, 8), (198, 197 * 64 + 10, 5), (204, 62 * 64 + 30, (10 << 8) + 10))


def torch(layer, attributes=10, resistance=10, skill=3):
    return Item(
        'Large Charm',
        'unique',
        'Hellfire Torch',
        ((83, layer, skill), *((s, 0, attributes) for s in ATTRIBUTES), *((s, 0, resistance) for s in RESISTS), *FIXED),
        complete=True,
    )


def cases():
    for player_class, layer, uses in USES:
        roles = tuple(g + '-hellfire-torch-gear-inventory-charm' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        item = torch(layer)
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', torch(layer, 20, 20), context, 'true'),
            ('attributes-perfect', torch(layer, 20, 10), context, 'true'),
            ('resistance-perfect', torch(layer, 10, 20), context, 'true'),
            (
                'empty-hydra',
                replace(item, raw_stats=(*item.raw_stats[:-1], (204, 62 * 64 + 30, 10 << 8))),
                context,
                'true',
            ),
            ('wrong-torch-class', torch(3), context, 'false'),
            ('two-class-bonuses', replace(item, raw_stats=(*item.raw_stats, (83, 3, 3))), context, 'false'),
            ('skill-too-low', torch(layer, skill=2), context, 'false'),
            ('skill-too-high', torch(layer, skill=4), context, 'false'),
            ('unread-class-bonus', replace(item, raw_stats=item.raw_stats[1:], complete=False), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-wearer', item, {'player_class': 'Paladin'}, 'false'),
            ('unknown-wearer', item, {}, 'unknown'),
            ('ethereal-impossible', replace(item, ethereal=True), context, 'false'),
            ('ethereal-unknown', replace(item, ethereal=None), context, 'unknown'),
            ('socket-impossible', replace(item, sockets=1), context, 'false'),
            ('socket-unknown', replace(item, sockets=None), context, 'unknown'),
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
            result = {'assessment': IsPartialDict(**expected)}
            if label in ('minimum', 'perfect', 'attributes-perfect', 'resistance-perfect'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=10, max=20),
                                roll_quality='perfect' if value == 20 else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in (*ATTRIBUTES, *RESISTS)
                        )
                    )
                )
            yield Case(
                id=f'torch-caster-tables/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(('89:0', '198:12618', '204:3998'), configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Hellfire Torch', 'Trade tier:') if truth == 'true' else ('Large Charm',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/400',
                    *(('pricing/raw/mr/planners/9e4fm0ow.json:/data',) if player_class == 'Warlock' else ()),
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{g}.html/sections/{i}'
                        for g, i in uses
                    ),
                ),
            )


CASES = tuple(cases())
