"""Exact cached premium throwing targets, separate from lower-roll candidate value."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RAW = ((17, 0, 450), (18, 0, 450), (19, 0, 250), (93, 0, 40), (188, 32, 2), (253, 0, 10), (198, 4225, 5))
KEYS = ('17:0', '18:0', '19:0', '93:0', '188:32', '253:0', '198:4225')


def cases():
    for hand in ('weapon', 'offhand'):
        role = 'double-throw-rare-planner-' + hand
        config = role + '-stats'
        ctx = {'player_class': 'Barbarian'}
        original = Item('Ghost Glaive', 'rare', raw_stats=RAW, ethereal=True, complete=True)
        variants = [
            ('ghost-glaive', original, ctx, 'true'),
            ('winged-axe', replace(original, base='Winged Axe'), ctx, 'true'),
            ('flying-axe', replace(original, base='Flying Axe'), ctx, 'true'),
            ('nonethereal', replace(original, ethereal=False), ctx, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
            ('unknown-cold-damage', replace(original, complete=False), ctx, 'unknown'),
            ('cold-damage', replace(original, raw_stats=(*RAW, (54, 0, 1), (55, 0, 2))), ctx, 'false'),
            (
                'unread-replenish',
                replace(original, raw_stats=tuple(r for r in RAW if r[0] != 253), complete=False),
                ctx,
                'unknown',
            ),
            ('known-no-replenish', replace(original, raw_stats=tuple(r for r in RAW if r[0] != 253)), ctx, 'false'),
            ('unidentified', replace(original, identified=False), ctx, 'false'),
            ('illegal-socket', replace(original, sockets=1, raw_stats=(*RAW, (194, 0, 1))), ctx, 'false'),
            ('unknown-sockets', replace(original, sockets=None), ctx, 'unknown'),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
        ]
        for label, ids, lower in (
            ('lower-ed', (17, 18), 449),
            ('lower-attack-rating', (19,), 249),
            ('lower-attack-speed', (93,), 30),
            ('one-combat-skill', (188,), 1),
            ('no-amplify', (198,), 0),
            ('slower-replenish', (253,), 5),
        ):
            variants.append(
                (
                    label,
                    replace(
                        original, raw_stats=tuple((s, layer, lower if s in ids else value) for s, layer, value in RAW)
                    ),
                    ctx,
                    'false',
                )
            )
        for label, item, context, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in KEYS})
                )
            yield Case(
                id=f'double-throw-premium-rares/{hand}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                evidence=(
                    'pricing/raw/mr/planners/db0106mf.json:/data/items/77',
                    'pricing/raw/mr/planners/db0106mf.json:/data/items/76',
                    'pricing/raw/mr/planners/db0106mf.json:/data/items/79',
                ),
            )


CASES = tuple(cases())
