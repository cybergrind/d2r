"""Native caster rings: keep combinations together and distinguish absent from unread."""

from dataclasses import replace
from itertools import combinations

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


LIGHTNING = Item('Ring', 'rare', raw_stats=((105, 0, 10), (9, 0, 50 * 256), (39, 0, 15), (43, 0, 15)))
NOVA = Item('Ring', 'rare', raw_stats=((105, 0, 10), (39, 0, 30), (41, 0, 30), (43, 0, 30)))


def cases():
    for role, original, build in (
        ('lightning-starter-ring', LIGHTNING, 'lightning-sorceress'),
        ('nova-starter-ring', NOVA, 'nova-sorceress-guide'),
    ):
        context = {'player_class': 'Sorceress'}
        variants = [('source-combination', original, context, 'true')]
        if role == 'lightning-starter-ring':
            variants.append(
                (
                    'premium-rolls',
                    replace(original, raw_stats=((105, 0, 10), (9, 0, 90 * 256), (39, 0, 30), (43, 0, 30))),
                    context,
                    'true',
                )
            )
            required = (105, 9, 39, 43)
        else:
            required = (105, 39, 41, 43)
            for elements in combinations((39, 41, 43, 45), 3):
                variants.append(
                    (
                        'elements-' + '-'.join(map(str, elements)),
                        replace(original, raw_stats=((105, 0, 10), *((s, 0, 30) for s in elements))),
                        context,
                        'true',
                    )
                )
        for stat in required:
            trimmed = tuple(row for row in original.raw_stats if row[0] != stat)
            variants.extend(
                (
                    (f'absent-{stat}', replace(original, raw_stats=trimmed, complete=True), context, 'false'),
                    (f'unread-{stat}', replace(original, raw_stats=trimmed), context, 'unknown'),
                )
            )
        without_fcr = replace(original, raw_stats=tuple(r for r in original.raw_stats if r[0] != 105), complete=True)
        companion = Item('Ring', 'rare', raw_stats=((105, 0, 10),))
        variants.append(
            (
                'other-ring-does-not-supply-fcr',
                without_fcr,
                {**context, 'player_equipment': {'ring_right': normalize(companion.capture()).to_dict()}},
                'false',
            )
        )
        for label, item, ctx, truth in variants:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true' and role == 'lightning-starter-ring':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('105:0', '9:0', '39:0', '43:0')
                        }
                    )
                )
            yield Case(
                id=f'sorceress-resource-rings/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if truth == 'true' else 'negative' if truth == 'false' else 'unknown',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=(role + '-stats',) if truth != 'true' else (),
                report_contains=('10% Faster Cast Rate',) if truth == 'true' else (),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/variants/0/player/Rings',),
            )


CASES = tuple(cases())
