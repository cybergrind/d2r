"""Read the actual mercenary jewel, preserving useful non-perfect affix rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.shaftstop_mercenaries import BASE as SHAFTSTOP
from tests.pricing.knowledge.assessment.item_bank.cases.vampire_gaze_setups import BASE as GAZE
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


SPECS = (
    ('dream-paladin', 1, 'shaftstop-ias-res', 'Paladin', 'Act 1 Cold', SHAFTSTOP, 93, 15, 'w670e0o0', False),
    ('dream-paladin', 2, 'shaftstop-ias-res', 'Paladin', 'Act 1 Cold', SHAFTSTOP, 93, 15, 'w670e0o0', True),
    ('lightning-strike-amazon', 1, 'shaftstop-ias-res', 'Amazon', 'Act 1 Cold', SHAFTSTOP, 93, 15, 'vc0106wm', True),
    ('smite-paladin', 1, 'gaze-max-res', 'Paladin', 'Act 2 Might', GAZE, 22, 11, '3q1ia0lw', False),
    ('smite-paladin', 2, 'gaze-max-res', 'Paladin', 'Act 2 Might', GAZE, 22, 11, '3q1ia0lw', False),
)


def jewel(stat, value, resistance):
    return SocketItem('Jewel', ((stat, 0, value), *((sid, 0, resistance) for sid in (39, 41, 43, 45))), True)


def cases():
    for build, variant, suffix, klass, merc, base, stat, minimum, planner, upgrade in SPECS:
        role = f'{build}-{variant}-merc-{suffix}'
        config = role + '-stats'
        child = jewel(stat, minimum, 11)
        item = replace(
            base,
            ethereal=True,
            sockets=1,
            socket_contents='filled',
            socket_items=(child,),
            raw_stats=(*base.raw_stats, *child.raw_stats),
        )
        perfect = jewel(stat, 15, 15)
        context = {'player_class': klass, 'mercenary_type': merc}
        examples = [
            ('minimum-affixes', item, context, 'true'),
            (
                'perfect-affixes',
                replace(item, socket_items=(perfect,), raw_stats=(*base.raw_stats, *perfect.raw_stats)),
                context,
                'true',
            ),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
            ('unknown-merc', item, {'player_class': klass}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {'mercenary_type': merc}, 'unknown'),
            ('nonethereal', replace(item, ethereal=False), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('missing-child', replace(item, socket_items=()), context, 'unknown'),
            ('partial-child', replace(item, socket_items=(replace(child, complete=False),)), context, 'unknown'),
            (
                'different-jewel',
                replace(item, socket_items=(jewel(22 if stat == 93 else 93, 15, 15),)),
                context,
                'false',
            ),
            ('resistance-below-tier', replace(item, socket_items=(jewel(stat, minimum, 10),)), context, 'false'),
            (
                'missing-poison-resist',
                replace(item, socket_items=(replace(child, raw_stats=child.raw_stats[:-1]),)),
                context,
                'false',
            ),
            ('attack-stat-below-tier', replace(item, socket_items=(jewel(stat, minimum - 1, 11),)), context, 'false'),
        ]
        if base == SHAFTSTOP:
            examples.append(('upgraded-base', replace(item, base='Boneweave'), context, 'true' if upgrade else 'false'))
        for label, candidate, ctx, truth in examples:
            expected = {
                'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth))),
                'trade_tier': IsPartialDict(status='reviewed'),
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in (f'{stat}:0', '39:0', '41:0', '43:0', '45:0', '36:0')
                        }
                    )
                )
            yield Case(
                id=f'merc-resistance-jewels/{role}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=(candidate.name, 'Trade tier:'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                    f'pricing/raw/mr/planners/{planner}.json:/data',
                    'third-parties/d2data/json/magicprefix.json:/337',
                ),
            )


CASES = tuple(cases())
