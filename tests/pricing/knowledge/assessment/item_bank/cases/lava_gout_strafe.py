"""Lava Gout is a Strafe proc alternative, not a guaranteed Enchant buff."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'strafe-amazon-lava-gout-equipment-tail-alternative'
CONFIG = ROLE + '-stats'
ITEM = Item(
    'Battle Gauntlets',
    'unique',
    'Lava Gout',
    ((39, 0, 24), (118, 0, 1), (198, 3338, 2), (93, 0, 20), (16, 0, 150), (48, 0, 13), (49, 0, 46)),
    named_table_id=235,
)


def cases():
    context = {'player_class': 'Amazon'}
    for label, item, ctx, truth in (
        ('native', ITEM, context, 'true'),
        (
            'maximum-defense',
            replace(ITEM, raw_stats=tuple((s, layer, 200 if s == 16 else value) for s, layer, value in ITEM.raw_stats)),
            context,
            'true',
        ),
        ('upgraded', replace(ITEM, base='Crusader Gauntlets'), context, 'true'),
        ('unread-enchant', replace(ITEM, raw_stats=tuple(r for r in ITEM.raw_stats if r[0] != 198)), context, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
        ('illegal-socket', replace(ITEM, sockets=1, raw_stats=(*ITEM.raw_stats, (194, 0, 1))), context, 'false'),
        ('unknown-sockets', replace(ITEM, sockets=None, socket_contents='unknown'), context, 'unknown'),
    ):
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        keys = ('93:0', '39:0', '118:0') + (() if label == 'unread-enchant' else ('198:3338',))
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in keys})
            )
        yield Case(
            id='lava-gout-strafe/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations=dict.fromkeys(
                ('153:0',) + (('198:3338',) if label == 'unread-enchant' else ()), (CONFIG,)
            ),
            report_contains=('Lava Gout', 'Trade tier:', '(150-200%)')
            if label in ('native', 'maximum-defense')
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/strafe-amazon/slots/Gloves/1',
                'third-parties/d2data/json/uniqueitems.json:/235',
            ),
        )


CASES = tuple(cases())
