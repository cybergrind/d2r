"""Fissure Lore is useful before reaching the pictured +3 staffmod target."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fissure-player-starter-lore'
NATIVE = ((127, 0, 1), (1, 0, 10), (41, 0, 30), (34, 0, 7), (138, 0, 2), (89, 0, 2), (194, 0, 2))
ITEM = Item(
    'Antlers',
    'normal',
    'Lore',
    (*NATIVE, (107, 234, 1)),
    ethereal=False,
    sockets=2,
    socket_contents='filled',
    runeword='Lore',
    socket_items=(SocketItem('Ort Rune'), SocketItem('Sol Rune')),
)


def cases():
    context = {'player_class': 'Druid'}
    examples = []
    for quality in ('normal', 'superior', 'low_quality'):
        for roll in (1, 2, 3):
            examples.append(
                (
                    f'{quality}-fissure-{roll}',
                    replace(ITEM, rarity=quality, raw_stats=(*NATIVE, (107, 234, roll))),
                    context,
                    'true',
                    'true' if roll == 3 else 'false',
                )
            )
    examples.extend(
        (
            ('missing-fissure', replace(ITEM, raw_stats=NATIVE, complete=True), context, 'false', 'false'),
            ('unread-fissure', replace(ITEM, raw_stats=NATIVE), context, 'unknown', 'unknown'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'false', 'false'),
            ('unread-ethereal', replace(ITEM, ethereal=None), context, 'unknown', 'false'),
            ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false', 'false'),
            ('unknown-class', ITEM, {}, 'unknown', 'false'),
        )
    )
    for label, item, ctx, truth, preferred in examples:
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE, rule_trace=IsPartialDict(truth=truth), preferences=[IsPartialDict(status=preferred)]
                )
            )
        }
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in ('107:234', '127:0')}
                )
            )
        yield Case(
            id='lore-fissure/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=('Lore', '+1 to All Skills'),
            evidence=(
                'pricing/data/wp-a-builds.json:/fissure-druid/variants/0',
                'third-parties/d2data/json/runes.json:/Lore',
            ),
        )


CASES = tuple(cases())
