"""Holy Bolt support's physical mercenary armor, not player spell damage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fist-of-the-heavens-paladin-4-merc-fortitude'
STATS = ((17, 0, 300), (18, 0, 300), (16, 0, 200), (105, 0, 25), (194, 0, 4))
ITEM = Item(
    'Sacred Armor',
    'normal',
    'Fortitude',
    (*STATS, *((stat, 0, 25) for stat in (39, 41, 43, 45))),
    ethereal=True,
    sockets=4,
    socket_contents='filled',
    runeword='Fortitude',
    socket_items=tuple(SocketItem(name + ' Rune') for name in ('El', 'Sol', 'Dol', 'Lo')),
)


def cases(
    role=ROLE,
    prefix='holy-bolt-fortitude',
    build='fist-of-the-heavens-paladin',
    variant=4,
    quality='normal',
    player_class='Paladin',
    mercenary='Act 2 Holy Freeze',
):
    original = replace(ITEM, rarity=quality)
    context = {'player_class': player_class, 'mercenary_type': mercenary}
    examples = [
        ('native-minimum', original, context, 'true'),
        (
            'maximum-resistance',
            replace(original, raw_stats=(*STATS, *((stat, 0, 30) for stat in (39, 41, 43, 45)))),
            context,
            'true',
        ),
        ('wrong-class', original, {**context, 'player_class': 'Warlock'}, 'false'),
        ('unknown-class', original, {'mercenary_type': mercenary}, 'unknown'),
        ('caster-mercenary', original, {**context, 'mercenary_type': 'Act 3 Fire'}, 'false'),
        ('unknown-mercenary', original, {'player_class': player_class}, 'unknown'),
        ('nonethereal', replace(original, ethereal=False), context, 'false'),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
        ('different-base', replace(original, base='Archon Plate'), context, 'false'),
        ('unidentified', replace(original, identified=False), context, 'false'),
        ('empty', replace(original, socket_items=(), socket_contents='empty'), context, 'false'),
        ('unknown-contents', replace(original, socket_items=(), socket_contents='unknown'), context, 'unknown'),
    ]
    for label, item, ctx, truth in examples:
        expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                        for key in ('17:0', '18:0', '16:0', '39:0', '41:0', '43:0', '45:0')
                    }
                )
            )
        yield Case(
            id=prefix + '/' + quality + '/' + label,
            item=item,
            context=ctx,
            covers=(role,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (role + '-stats',),
            absent_stat_configurations={'105:0': (role + '-stats',)},
            report_contains=('Fortitude',),
            evidence=(
                f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                'third-parties/d2data/json/runes.json:/Fortitude',
            ),
        )


CASES = tuple(case for quality in ('normal', 'superior', 'low_quality') for case in cases(quality=quality))
