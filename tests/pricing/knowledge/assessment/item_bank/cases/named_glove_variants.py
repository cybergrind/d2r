"""Build-specific glove uses, including FCR boundaries and upgraded Magefist."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


LAYING = Item('Bramble Mitts', 'set', 'Laying of Hands', ((93, 0, 20), (121, 0, 350), (39, 0, 50)))
TRANG = Item('Heavy Bracers', 'set', "Trang-Oul's Claws", ((105, 0, 20), (43, 0, 30)))
MAGEFIST = Item('Crusader Gauntlets', 'unique', 'Magefist', ((105, 0, 20), (27, 0, 25), (126, 1, 1)))
USES = (
    ('mirrored-blades-warlock-guide', 1, 'laying-hands', 'Warlock', LAYING, None, ('93:0', '121:0')),
    ('mirrored-blades-warlock-guide', 2, 'laying-hands', 'Warlock', LAYING, None, ('93:0', '121:0')),
    ('dream-paladin', 0, 'laying-hands', 'Paladin', LAYING, None, ('93:0', '121:0')),
    ('dream-paladin', 1, 'laying-hands', 'Paladin', LAYING, None, ('93:0', '121:0')),
    ('echoing-strike-warlock-guide', 1, 'trang-claws', 'Warlock', TRANG, 125, ('105:0', '43:0')),
    ('echoing-strike-warlock-guide', 2, 'trang-claws', 'Warlock', TRANG, 125, ('105:0', '43:0')),
    ('echoing-strike-warlock-guide', 3, 'trang-claws', 'Warlock', TRANG, None, ('105:0', '43:0')),
    ('blizzard-sorceress', 1, 'trang-claws', 'Sorceress', TRANG, 105, ('105:0', '43:0')),
    ('fissure-druid', 3, 'magefist', 'Druid', MAGEFIST, None, ('105:0', '126:1', '27:0')),
)


def cases():
    for build, variant, suffix, klass, item, fcr, keys in USES:
        role = f'{build}-{variant}-{suffix}'
        config = role + '-stats'
        context = {'player_class': klass, **({'player_total_fcr': fcr} if fcr else {})}
        examples = [
            ('useful', item, context, 'true'),
            ('wrong-class', item, {**context, 'player_class': 'Necromancer'}, 'false'),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        if fcr:
            examples.extend(
                (
                    ('fcr-short', item, {**context, 'player_total_fcr': fcr - 1}, 'false'),
                    ('fcr-unknown', item, {'player_class': klass}, 'unknown'),
                )
            )
        if item == MAGEFIST:
            examples.extend(
                (base, replace(item, base=base), context, 'false') for base in ('Light Gauntlets', 'Battle Gauntlets')
            )
        for label, candidate, ctx, truth in examples:
            assessment = {
                'roles': Contains(IsPartialDict(id=role, side='player', rule_trace=IsPartialDict(truth=truth)))
            }
            if truth == 'true':
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
                assessment['trade_tier'] = IsPartialDict(status='reviewed')
            yield Case(
                id=f'named-glove-variants/{role}/{label}',
                item=candidate,
                context=ctx,
                expected={
                    'assessment': IsPartialDict(**assessment),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=(candidate.name, *(['Trade tier:'] if truth == 'true' else [])),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',),
            )


CASES = tuple(cases())
