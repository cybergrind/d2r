"""Native minimum affix rolls for the Zeal rare Berserker Axe example."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'zeal-paladin-ethereal-rare-axe'
CONTEXT = {'player_class': 'Paladin', 'player_level': 80}
STATS = ((17, 0, 201), (18, 0, 201), (93, 0, 40), (22, 0, 15), (218, 0, 4), (224, 0, 33), (252, 0, 3), (141, 0, 40))
AFFIXES = (('prefix', 420), ('prefix', 669), ('prefix', 526), ('suffix', 402), ('suffix', 169), ('suffix', 201))
ITEM = Item(
    'Berserker Axe',
    'rare',
    'Ghoul Bite',
    STATS,
    ethereal=True,
    sockets=2,
    socket_contents='filled',
    socket_items=(SocketItem('Lo Rune'), SocketItem('Lo Rune')),
    affix_records=AFFIXES,
)


def cases():
    rows = [
        ('native-low-rolls', 'positive', ITEM, CONTEXT),
        (
            'perfect-ed',
            'positive',
            replace(ITEM, raw_stats=tuple((s, p, 300 if s in (17, 18) else v) for s, p, v in STATS)),
            CONTEXT,
        ),
        (
            'no-repair-affix',
            'negative',
            replace(ITEM, affix_records=tuple(a for a in AFFIXES if a != ('suffix', 402))),
            CONTEXT,
        ),
        ('unknown-affixes', 'unknown', replace(ITEM, affix_records=None), CONTEXT),
        ('nonethereal', 'negative', replace(ITEM, ethereal=False), CONTEXT),
        ('unknown-ethereal', 'unknown', replace(ITEM, ethereal=None), CONTEXT),
        ('wrong-class', 'negative', ITEM, {'player_class': 'Sorceress'}),
        ('unknown-class', 'unknown', ITEM, {}),
        ('empty', 'negative', replace(ITEM, socket_contents='empty', socket_items=()), CONTEXT),
        (
            'wrong-fillers',
            'negative',
            replace(ITEM, socket_items=(SocketItem('Ist Rune'), SocketItem('Ist Rune'))),
            CONTEXT,
        ),
        ('unknown-fillers', 'unknown', replace(ITEM, socket_items=()), CONTEXT),
        ('one-socket', 'negative', replace(ITEM, sockets=1, socket_items=(SocketItem('Lo Rune'),)), CONTEXT),
    ]
    result = []
    for label, scenario, item, context in rows:
        expected = {'roles': Contains(IsPartialDict(id=ROLE))}
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        k: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for k in ('17:0', '18:0', '93:0', '22:0', '218:0', '224:0', '252:0', '141:0')
                    }
                )
            )
        result.append(
            Case(
                id='zeal/rare-axe/' + label,
                item=item,
                context=context,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                report_contains=('Berserker Axe',),
                evidence=('pricing/raw/mr/planners/n8010616.json:/data/items/108',),
            )
        )
    return tuple(result)


CASES = cases()
