"""Independently transcribed rare imbue examples retain their exact combinations."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RECIPES = (
    (
        'axe',
        'Flying Axe',
        80,
        ('weapon', 'offhand'),
        ((17, 0, 150), (18, 0, 150), (253, 0, 10), (93, 0, 20), (188, 32, 2), (39, 0, 20)),
    ),
    (
        'knife',
        'Flying Knife',
        81,
        ('weapon', 'offhand'),
        ((188, 32, 2), (19, 0, 121), (17, 0, 200), (18, 0, 200), (198, 4225, 5), (62, 0, 6), (253, 0, 10)),
    ),
    (
        'harpoon',
        'Winged Harpoon',
        143,
        ('weapon',),
        ((253, 0, 10), (93, 0, 20), (60, 0, 9), (17, 0, 200), (18, 0, 200), (188, 32, 2)),
    ),
)


def cases():
    for family, base, planner_id, hands, raw in RECIPES:
        for hand in hands:
            role = f'double-throw-imbue-{family}-{hand}'
            config = role + '-stats'
            original = Item(base, 'rare', raw_stats=raw, ethereal=True, complete=True)
            ctx = {'player_class': 'Barbarian'}
            variants = [
                ('planner-example', original, ctx, 'true'),
                ('nonethereal', replace(original, ethereal=False), ctx, 'false'),
                ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown'),
                ('unknown-cold', replace(original, complete=False), ctx, 'unknown'),
                ('cold-damage', replace(original, raw_stats=(*raw, (54, 0, 1), (55, 0, 2))), ctx, 'false'),
                ('unidentified', replace(original, identified=False), ctx, 'false'),
                ('illegal-socket', replace(original, sockets=1, raw_stats=(*raw, (194, 0, 1))), ctx, 'false'),
                ('unknown-sockets', replace(original, sockets=None), ctx, 'unknown'),
                ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
            ]
            # Both ED components belong to one affix; all other missing stats retain
            # the rest of the example, rather than substituting an unrelated weapon.
            for stat in sorted({s for s, _, _ in raw} - {18}):
                remove = (17, 18) if stat == 17 else (stat,)
                reduced = tuple(r for r in raw if r[0] not in remove)
                variants.extend(
                    (
                        (f'absent-{stat}', replace(original, raw_stats=reduced), ctx, 'false'),
                        (f'unread-{stat}', replace(original, raw_stats=reduced, complete=False), ctx, 'unknown'),
                    )
                )
            for label, item, context, truth in variants:
                active = truth == 'true'
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                f'{stat}:{layer}': IsPartialDict(configuration_ids=Contains(config))
                                for stat, layer, _ in raw
                            }
                        )
                    )
                yield Case(
                    id=f'double-throw-imbue-examples/{family}/{hand}/{label}',
                    item=item,
                    context=context,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else (config,),
                    evidence=(f'pricing/raw/mr/planners/db0106mf.json:/data/items/{planner_id}',),
                )


CASES = tuple(cases())
