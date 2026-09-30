"""Fixed SoJ skill/resource utility across independently reviewed build variants."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


VARIANTS = (
    ('blizzard-sorceress', 'Sorceress', ((1, 105),)),
    ('enchant-sorceress', 'Sorceress', ((1, None),)),
    ('fissure-druid', 'Druid', ((1, 99), (2, None), (3, None))),
    ('lightning-sentry-assassin', 'Assassin', ((1, 65),)),
    ('lightning-sorceress', 'Sorceress', ((1, 117),)),
    ('nova-sorceress-guide', 'Sorceress', ((1, 105), (2, None), (3, None))),
    ('poison-nova-necromancer', 'Necromancer', ((1, 125), (2, 125))),
    ('summoner-necromancer-guide', 'Necromancer', ((1, 125), (2, 75))),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 29),
    ('summoner-warlock-guide', 'Warlock', 29),
    ('fire-wall-sorceress-guide', 'Sorceress', 30),
    ('frozen-orb-meteor-sorceress', 'Sorceress', 29),
    ('frozen-orb-sorceress', 'Sorceress', 29),
    ('hydra-sorceress', 'Sorceress', 29),
)


def uses():
    for guide, player_class, variants in VARIANTS:
        for variant, fcr in variants:
            yield (
                f'{guide}-{variant}-soj',
                player_class,
                fcr,
                False,
                (f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}'),
            )
    for guide, player_class, section in TABLES:
        yield (
            guide + '-the-stone-of-jordan-caster-core-gear',
            player_class,
            None,
            True,
            (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
            ),
        )


def cases():
    # Native unique122; flat mana uses 8 fractional bits, unlike percent mana.
    item = Item(
        'Ring',
        'unique',
        'The Stone of Jordan',
        raw_stats=(
            (9, 0, 20 << 8),
            (77, 0, 25),
            (50, 0, 1),
            (51, 0, 12),
            (127, 0, 1),
        ),
        complete=True,
    )
    for role, player_class, fcr, table, source in uses():
        context = {'player_class': player_class}
        if fcr is not None:
            context['player_total_fcr'] = fcr
        examples = [
            ('native', item, context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, dict(context, player_class='Barbarian'), 'false'),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ('invalid-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        if fcr is not None:
            examples.extend(
                (
                    ('below-cast-breakpoint', item, dict(context, player_total_fcr=fcr - 1), 'false'),
                    ('unknown-cast-total', item, {'player_class': player_class}, 'unknown'),
                )
            )
        if table:
            examples.extend(
                (
                    ('illegal-socket', replace(item, sockets=1), context, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                )
            )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['trade_tier'] = IsPartialDict(tier='high')
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('127:0', '9:0', '77:0')
                        }
                    )
                )
            yield Case(
                id=f'stone-of-jordan-roles/{role}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=dict.fromkeys(('50:0', '51:0'), (role + '-stats',)),
                report_contains=('The Stone of Jordan', 'Trade tier: high') if truth == 'true' else ('Ring',),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/122'),
            )


CASES = tuple(cases())
