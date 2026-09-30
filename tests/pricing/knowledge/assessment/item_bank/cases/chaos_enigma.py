"""Chaos Prep Enigma utility survives ordinary rolls, but not unknown wearer facts."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'berserk-barbarian-4-player-enigma'
STATS = ((127, 0, 2), (97, 54, 1), (96, 0, 45), (220, 0, 6), (240, 0, 8), (36, 0, 8), (76, 0, 5), (194, 0, 3))
ITEM = Item(
    'Mage Plate',
    'normal',
    'Enigma',
    (*STATS, (31, 0, 975)),
    sockets=3,
    socket_contents='filled',
    runeword='Enigma',
    socket_items=tuple(SocketItem(name + ' Rune') for name in ('Jah', 'Ith', 'Ber')),
)


def cases():
    context = {'player_class': 'Barbarian'}
    examples = [
        ('minimum-defense', ITEM, context, 'true'),
        ('maximum-defense', replace(ITEM, raw_stats=(*STATS, (31, 0, 1036))), context, 'true'),
        ('superior', replace(ITEM, rarity='superior', raw_stats=(*STATS, (16, 0, 15), (31, 0, 1076))), context, 'true'),
        ('low-quality', replace(ITEM, rarity='low_quality', raw_stats=(*STATS, (31, 0, 870))), context, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Paladin'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('different-base', replace(ITEM, base='Archon Plate'), context, 'false'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
        ('empty', replace(ITEM, socket_contents='empty', socket_items=()), context, 'false'),
        ('unknown-contents', replace(ITEM, socket_contents='unknown', socket_items=()), context, 'unknown'),
    ]
    for label, item, ctx, truth in examples:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('127:0', '97:54', '96:0', '220:0', '240:0', '31:0', '36:0', '76:0')
                    }
                )
            )
        yield Case(
            id='chaos-enigma/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=('Enigma',),
            evidence=('pricing/raw/mr/planners/rb1d60lu.json:/data', 'third-parties/d2data/json/runes.json:/Enigma'),
        )


CASES = tuple(cases())
