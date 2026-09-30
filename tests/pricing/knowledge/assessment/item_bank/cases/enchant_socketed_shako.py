"""Enchant farming helmet uses the actual Defender's Fire, not a lookalike jewel."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.caster_socketed_named import FIRE
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'enchant-sorceress-2-harlequin-defender-fire'
ITEM = Item(
    'Shako',
    'unique',
    'Harlequin Crest',
    ((127, 0, 2), (80, 0, 65), (329, 0, 5), (333, 0, 5)),
    sockets=1,
    socket_contents='filled',
    socket_items=(FIRE,),
)


def cases():
    examples = [
        ('minimum', ITEM, {'player_class': 'Sorceress'}, 'true'),
        (
            'ordinary-jewel',
            replace(ITEM, socket_items=(replace(FIRE, name=None, unique_table_id=None),)),
            {'player_class': 'Sorceress'},
            'false',
        ),
        ('empty', replace(ITEM, socket_contents='empty', socket_items=()), {'player_class': 'Sorceress'}, 'false'),
        ('unread', replace(ITEM, socket_items=()), {'player_class': 'Sorceress'}, 'unknown'),
        (
            'partial',
            replace(ITEM, socket_items=(replace(FIRE, complete=False, raw_stats=()),)),
            {'player_class': 'Sorceress'},
            'unknown',
        ),
        ('ethereal', replace(ITEM, ethereal=True), {'player_class': 'Sorceress'}, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), {'player_class': 'Sorceress'}, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Warlock'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('low-teleport-fcr', ITEM, {'player_class': 'Sorceress', 'player_total_fcr': 0}, 'true'),
    ]
    for label, item, context, truth in examples:
        config = ROLE + '-stats'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(config))
                        for key in ('127:0', '80:0', '329:0', '333:0')
                    }
                )
            )
        yield Case(
            id='enchant-socketed-shako/' + label,
            item=item,
            context=context,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (config,),
            report_contains=('Harlequin Crest',),
            evidence=('pricing/data/wp-a-builds.json:/enchant-sorceress/variants/2',),
        )


CASES = tuple(cases())
