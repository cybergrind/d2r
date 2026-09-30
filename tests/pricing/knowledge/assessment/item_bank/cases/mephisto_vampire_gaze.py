"""The Lightning Sorceress Mephisto mercenary, not a generic Ubers loadout."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'lightning-sorc-mephisto-gaze-merc'
CONFIG = ROLE + '-stats'
ITEM = Item(
    'Grim Helm',
    'unique',
    'Vampire Gaze',
    (
        (60, 0, 6),
        (62, 0, 6),
        (36, 0, 15),
        (35, 0, 10),
        (16, 0, 100),
        (54, 0, 6),
        (55, 0, 22),
        (56, 0, 100),
        *((stat, 0, 15) for stat in (39, 41, 43, 45)),
    ),
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Um Rune'),),
)
CONTEXT = {'player_class': 'Sorceress', 'mercenary_type': 'Act 5 Frenzy', 'activity': 'Uber Mephisto'}


def cases():
    examples = (
        ('native-minimum', ITEM, CONTEXT, 'positive', None),
        ('ethereal', replace(ITEM, ethereal=True), CONTEXT, 'positive', None),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'positive', None),
        ('upgraded', replace(ITEM, base='Bone Visage'), CONTEXT, 'positive', None),
        ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 2 Might'}, 'negative', 'Mercenary type'),
        (
            'unknown-mercenary',
            ITEM,
            {'player_class': 'Sorceress', 'activity': 'Uber Mephisto'},
            'unknown',
            'Mercenary type',
        ),
        ('generic-ubers', ITEM, {**CONTEXT, 'activity': 'Ubers'}, 'negative', 'Activity'),
        ('other-uber', ITEM, {**CONTEXT, 'activity': 'Uber Diablo'}, 'negative', 'Activity'),
        (
            'unknown-activity',
            ITEM,
            {'player_class': 'Sorceress', 'mercenary_type': 'Act 5 Frenzy'},
            'unknown',
            'Activity',
        ),
        ('wrong-rune', replace(ITEM, socket_items=(SocketItem('Ral Rune'),)), CONTEXT, 'negative', 'socket'),
        ('unread-rune', replace(ITEM, socket_items=()), CONTEXT, 'unknown', 'socket'),
        ('empty-socket', replace(ITEM, socket_contents='empty', socket_items=()), CONTEXT, 'negative', 'socket'),
        ('unknown-sockets', replace(ITEM, sockets=None), CONTEXT, 'unknown', 'socket'),
    )
    for label, item, context, scenario, failed in examples:
        role = {'id': ROLE, 'side': 'merc', 'status': 'partial', 'rule_trace': IsPartialDict(truth='true')}
        if failed == 'socket':
            role['socket_requirement'] = IsPartialDict(item='Um Rune', confirmed=False)
        elif failed:
            label_text = 'Mercenary type: Act 5 Frenzy' if failed == 'Mercenary type' else 'Activity: Uber Mephisto'
            role['dependencies'] = Contains(
                IsPartialDict(label=label_text, status='unknown' if scenario == 'unknown' else 'false')
            )
        else:
            role['socket_requirement'] = IsPartialDict(item='Um Rune', confirmed=True)
            role['dependencies'] = [
                IsPartialDict(label='Mercenary type: Act 5 Frenzy', status='true'),
                IsPartialDict(label='Activity: Uber Mephisto', status='true'),
            ]
        expected = {'roles': Contains(IsPartialDict(**role)), 'trade_tier': IsPartialDict(status='reviewed')}
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('60:0', '36:0')}
                )
            )
        yield Case(
            id=f'lightning-sorceress/mephisto-gaze/{label}',
            item=item,
            context=context,
            covers=(ROLE,),
            scenario=scenario,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if scenario == 'positive' else (CONFIG,),
            absent_stat_configurations={'62:0': (CONFIG,), '16:0': (CONFIG,)},
            report_contains=('Vampire Gaze', 'Trade tier:'),
            evidence=(
                'pricing/data/wp-a-builds.json:/lightning-sorceress/variants/3/merc',
                'third-parties/d2data/json/uniqueitems.json:/208',
            ),
        )


CASES = tuple(cases())
