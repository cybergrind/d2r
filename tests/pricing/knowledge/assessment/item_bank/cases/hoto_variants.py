"""One Heart of the Oak supplies its own casting stats, not a dual-weapon total."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ITEM = Item(
    'Flail',
    'normal',
    'Heart of the Oak',
    (
        (127, 0, 3),
        (105, 0, 40),
        (77, 0, 15),
        (74, 0, 20),
        (2, 0, 10),
        *((sid, 0, 30) for sid in (39, 41, 43, 45)),
        (194, 0, 4),
    ),
    ethereal=True,
    sockets=4,
    socket_contents='filled',
    runeword='Heart of the Oak',
    socket_items=tuple(SocketItem(name) for name in ('Ko Rune', 'Vex Rune', 'Pul Rune', 'Thul Rune')),
)
USES = (
    ('fire-blast-assassin', 1, 'Assassin', False),
    ('fissure-druid', 1, 'Druid', False),
    ('fissure-druid', 2, 'Druid', False),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', False),
    ('lightning-sentry-assassin', 2, 'Assassin', False),
    ('lightning-sorceress', 1, 'Sorceress', False),
    ('gold-find-barbarian', 1, 'Barbarian', True),
    ('gold-find-barbarian', 2, 'Barbarian', True),
    ('gold-find-barbarian', 3, 'Barbarian', False),
    ('summoner-necromancer-guide', 1, 'Necromancer', True),
)


def cases():
    for build, variant, klass, eth_required in USES:
        role = f'{build}-{variant}-heart-oak'
        config = role + '-stats'
        context = {'player_class': klass}
        perfect = replace(
            ITEM,
            raw_stats=tuple(
                (sid, layer, 40 if sid in (39, 41, 43, 45) else value) for sid, layer, value in ITEM.raw_stats
            ),
        )
        examples = (
            ('minimum-resistance', ITEM, context, 'true'),
            ('perfect-resistance', perfect, context, 'true'),
            ('superior-base', replace(ITEM, rarity='superior'), context, 'true'),
            ('low-quality-base', replace(ITEM, rarity='low_quality'), context, 'true'),
            ('wrong-class', ITEM, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', ITEM, {}, 'unknown'),
            ('nonethereal', replace(ITEM, ethereal=False), context, 'false' if eth_required else 'true'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown' if eth_required else 'true'),
            ('different-base', replace(ITEM, base='Knout'), context, 'false'),
            ('component-below-build-breakpoint', ITEM, {**context, 'player_total_fcr': 40}, 'true'),
            ('no-second-weapon', ITEM, {**context, 'player_swap_items': []}, 'true'),
        )
        examples += (
            ('unidentified', replace(ITEM, identified=False), context, 'false'),
            ('unknown-contents', replace(ITEM, socket_contents='unknown', socket_items=()), context, 'unknown'),
            (
                'wrong-socket-count',
                replace(
                    ITEM,
                    sockets=3,
                    socket_items=ITEM.socket_items[:3],
                    raw_stats=tuple((sid, layer, 3 if sid == 194 else raw) for sid, layer, raw in ITEM.raw_stats),
                ),
                context,
                'false',
            ),
        )
        # Different legal qualities need their own negative and unknown cases;
        # normal-quality boundaries cannot establish those paths.
        for quality in ('superior', 'low_quality'):
            examples += (
                (quality + '-wrong-class', replace(ITEM, rarity=quality), {'player_class': 'Amazon'}, 'false'),
                (quality + '-unknown-class', replace(ITEM, rarity=quality), {}, 'unknown'),
                (
                    quality + '-unknown-ethereal',
                    replace(ITEM, rarity=quality, ethereal=None),
                    context,
                    'unknown' if eth_required else 'true',
                ),
            )
        for label, item, ctx, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, side='player', rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('127:0', '105:0', '77:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'hoto-variants/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=('Heart of the Oak', '+3 to All Skills'),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                    'third-parties/d2data/json/runes.json:/Heart of the Oak',
                ),
            )


CASES = tuple(cases())
