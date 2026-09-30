"""Independent planner ring recipes; no modifier pooling across alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ALL_RES = ((39, 0, 11), (41, 0, 11), (43, 0, 11), (45, 0, 11))
# Literal examples transcribed from planner n8010616; life and mana use native 8-bit fixed point.
RECIPES = (
    (15, 162, ((105, 0, 10), (19, 0, 120), (60, 0, 8), (62, 0, 6), *ALL_RES, (80, 0, 10)), 60),
    (73, 163, ((105, 0, 10), (19, 0, 120), (60, 0, 8), (7, 0, 40 * 256), *ALL_RES, (80, 0, 10)), 60),
    (171, 164, ((105, 0, 10), (19, 0, 120), (60, 0, 8), *ALL_RES, (80, 0, 25)), 60),
    (55, 165, ((19, 0, 120), (62, 0, 6), (60, 0, 8), (9, 0, 90 * 256), (80, 0, 15), *ALL_RES), 62),
    (41, 166, ((60, 0, 6), (62, 0, 4), (19, 0, 80), (39, 0, 8), (41, 0, 8), (43, 0, 8), (45, 0, 8)), 62),
    (154, 167, ((19, 0, 100), (62, 0, 5), (39, 0, 15), (41, 0, 15)), 62),
)


def cases():
    context = {'player_class': 'Paladin'}
    for ref, span, stats, drain in RECIPES:
        role = f'zeal-paladin-rare-ring-{ref}'
        config = role + '-stats'
        original = Item('Ring', 'rare', raw_stats=stats)
        without_drain = tuple(row for row in stats if row[0] != drain)
        variants = [
            ('planner-example', original, context, 'true'),
            ('missing-leech', replace(original, raw_stats=without_drain, complete=True), context, 'false'),
            ('unread-leech', replace(original, raw_stats=without_drain), context, 'unknown'),
            (
                'missing-attack-rating',
                replace(original, raw_stats=tuple(row for row in stats if row[0] != 19), complete=True),
                context,
                'false',
            ),
            (
                'missing-resistances',
                replace(
                    original, raw_stats=tuple(row for row in stats if row[0] not in (39, 41, 43, 45)), complete=True
                ),
                context,
                'false',
            ),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('invalid-ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('invalid-socket', replace(original, sockets=1, raw_stats=(*stats, (194, 0, 1))), context, 'false'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ]
        other_ring = replace(original, raw_stats=tuple(row for row in stats if row[0] == drain))
        variants.append(
            (
                'other-ring-cannot-supply-leech',
                replace(original, raw_stats=without_drain, complete=True),
                {**context, 'player_equipment': {'ring_right': normalize(other_ring.capture()).to_dict()}},
                'false',
            )
        )
        if any(s == 105 for s, _, _ in stats):
            variants.append(
                (
                    'missing-cast-rate',
                    replace(original, raw_stats=tuple(row for row in stats if row[0] != 105), complete=True),
                    context,
                    'false',
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{stat}:{layer}': IsPartialDict(configuration_ids=Contains(config))
                            for stat, layer, _ in stats
                        }
                    )
                )
            yield Case(
                id=f'zeal-rare-ring-combinations/{ref}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**assessment)},
                absent_configurations=() if active else (config,),
                report_contains=('Ring', 'Attack Rating') if active else (),
                evidence=(
                    f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    f'pricing/raw/mr/planners/n8010616.json:decoded/items/{ref}',
                ),
            )


CASES = tuple(cases())
