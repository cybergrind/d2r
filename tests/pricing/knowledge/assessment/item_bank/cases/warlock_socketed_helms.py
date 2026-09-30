"""Warlock named helmets need the actual socket payload and applicable companions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.caster_socketed_named import FIRE
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_light_helms import CHILD as LIGHT
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'echoing-ubers-hellwarden-guardian-light',
        Item(
            'Death Mask',
            'unique',
            "Hellwarden's Will",
            ((127, 0, 1), (105, 0, 20), (358, 0, 10), (357, 0, 5)),
            sockets=1,
            socket_contents='filled',
            socket_items=(LIGHT,),
        ),
        {'player_class': 'Warlock', 'player_items': ['Sling', 'Renewed Black Cleft']},
        ('127:0', '105:0', '358:0'),
    ),
    (
        'fire-warlock-guide-2-harlequin-defender-fire',
        Item(
            'Shako',
            'unique',
            'Harlequin Crest',
            ((127, 0, 2), (80, 0, 65), (329, 0, 5), (333, 0, 5)),
            sockets=1,
            socket_contents='filled',
            socket_items=(FIRE,),
        ),
        {'player_class': 'Warlock'},
        ('127:0', '80:0', '329:0', '333:0'),
    ),
)


def cases():
    for role, item, context, keys in SPECS:
        child = item.socket_items[0]
        examples = [
            ('minimum', item, context, 'true', True),
            ('wrong-jewel', replace(item, socket_items=(FIRE if child == LIGHT else LIGHT,)), context, 'false', False),
            (
                'ordinary-jewel',
                replace(item, socket_items=(replace(child, name=None, unique_table_id=None),)),
                context,
                'false',
                False,
            ),
            (
                'partial-jewel',
                replace(item, socket_items=(replace(child, complete=False, raw_stats=()),)),
                context,
                'unknown',
                False,
            ),
            ('unread-jewel', replace(item, socket_items=()), context, 'unknown', False),
            ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false', False),
            ('ethereal', replace(item, ethereal=True), context, 'false', False),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False),
            ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'false', False),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', False),
        ]
        if role.startswith('echoing'):
            examples += [
                ('missing-sling', item, {**context, 'player_items': ['Renewed Black Cleft']}, 'true', False),
                ('missing-sunder', item, {**context, 'player_items': ['Sling']}, 'true', False),
                ('unknown-companions', item, {'player_class': 'Warlock'}, 'true', False),
            ]
        for label, candidate, ctx, truth, active in examples:
            config = role + '-stats'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'warlock-socketed-helm/{role}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario='positive'
                if active
                else 'unknown'
                if 'unknown' in label or 'unread' in label or 'partial' in label
                else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations={'357:0': (config,)} if role.startswith('echoing') else {},
                report_contains=(item.name,),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/423',
                    'third-parties/d2data/json/uniqueitems.json:/425',
                ),
            )


CASES = tuple(cases())
