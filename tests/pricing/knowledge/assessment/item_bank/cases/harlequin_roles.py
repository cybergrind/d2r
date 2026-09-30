"""Shako caster-table and MF component utility with native defense and socket boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


FARMING = (
    ('blizzard-sorceress', 'Sorceress', 105, None),
    ('double-throw-barbarian-guide', 'Barbarian', None, None),
    ('echoing-strike-warlock-guide', 'Warlock', 125, None),
    ('enchant-sorceress', 'Sorceress', None, None),
    ('fire-warlock-guide', 'Warlock', None, None),
    ('meteor-sorceress', 'Sorceress', 105, 60),
    ('lightning-sentry-assassin', 'Assassin', 102, None),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 29),
    ('summoner-warlock-guide', 'Warlock', 29),
    ('fire-wall-sorceress-guide', 'Sorceress', 30),
    ('frozen-orb-meteor-sorceress', 'Sorceress', 29),
    ('frozen-orb-sorceress', 'Sorceress', 29),
    ('hydra-sorceress', 'Sorceress', 29),
    ('summoner-necromancer-guide', 'Necromancer', 33),
)


def uses():
    for guide, player_class, fcr, fhr in FARMING:
        yield (
            guide + '-2-harlequin',
            player_class,
            fcr,
            fhr,
            False,
            (f'pricing/data/wp-a-builds.json:/{guide}/variants/2'),
        )
    for guide, player_class, section in TABLES:
        suffix = 'summoner-caster-gear' if player_class == 'Necromancer' else 'caster-core-gear'
        yield (
            guide + '-harlequin-crest-' + suffix,
            player_class,
            None,
            None,
            True,
            (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
            ),
        )


def cases():
    item = Item(
        'Shako',
        'unique',
        'Harlequin Crest',
        raw_stats=(
            (31, 0, 98),
            (127, 0, 2),
            (80, 0, 50),
            (36, 0, 10),
            (216, 0, 12 << 8),
            (217, 0, 12 << 8),
            (0, 0, 2),
            (1, 0, 2),
            (2, 0, 2),
            (3, 0, 2),
        ),
        viewer_level=80,
        owned_stats=((31, 0, 98),),
    )
    for role, player_class, fcr, fhr, table, source in uses():
        context = {'player_class': player_class}
        if fcr is not None:
            context['player_total_fcr'] = fcr
        if fhr is not None:
            context['player_total_fhr'] = fhr
        examples = [
            ('minimum-defense', item, context, 'true'),
            ('unknown-base-defense', replace(item, owned_stats=None), context, 'true'),
            (
                'maximum-defense',
                replace(item, raw_stats=((31, 0, 141), *item.raw_stats[1:]), owned_stats=((31, 0, 141),)),
                context,
                'true',
            ),
            ('open-socket', replace(item, sockets=1), context, 'true'),
            ('unread-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, dict(context, player_class='Paladin'), 'false'),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
        ]
        if table:
            examples.extend(
                (
                    ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                )
            )
        if fcr is not None:
            examples.extend(
                (
                    ('below-cast-breakpoint', item, dict(context, player_total_fcr=fcr - 1), 'false'),
                    (
                        'unknown-cast-total',
                        item,
                        {k: v for k, v in context.items() if k != 'player_total_fcr'},
                        'unknown',
                    ),
                )
            )
        if fhr is not None:
            examples.extend(
                (
                    ('below-recovery-breakpoint', item, dict(context, player_total_fhr=fhr - 1), 'false'),
                    (
                        'unknown-recovery-total',
                        item,
                        {k: v for k, v in context.items() if k != 'player_total_fhr'},
                        'unknown',
                    ),
                )
            )
        keys = ('127:0', '80:0', '36:0', '216:0', '217:0', '0:0', '1:0', '2:0', '3:0') if table else ('127:0', '80:0')
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'harlequin-roles/{role}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                report_contains=(
                    ('Harlequin Crest', 'Trade tier:', f'Defense: {141 if label == "maximum-defense" else 98} (98-141)')
                    if truth == 'true' and label != 'unknown-base-defense'
                    else ('Shako',)
                ),
                report_absent=('(98-141)',) if label == 'unknown-base-defense' else (),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/248'),
            )


CASES = tuple(cases())
