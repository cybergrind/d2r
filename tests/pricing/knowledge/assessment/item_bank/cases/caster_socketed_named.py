"""Actual socket payloads for caster magic-find helmets and Uber caster armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.griffon_thunder import CHILD as THUNDER
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


FIRE = SocketItem(
    'Colossal Jewel',
    ((329, 0, 5), (333, 0, 5), (48, 0, 20), (49, 0, 60), (85, 0, 3), (80, 0, 15), (79, 0, 25), (201, 46 * 64 + 25, 1)),
    complete=True,
    name="Defender's Fire",
    unique_table_id=423,
)
RESIST = SocketItem('Jewel', ((99, 0, 7), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15)), complete=True)
SPECS = (
    (
        'lightning-sentry-assassin',
        2,
        'harlequin',
        'Shako',
        'Harlequin Crest',
        THUNDER,
        FIRE,
        ((127, 0, 2), (80, 0, 65), (330, 0, 5), (334, 0, 5)),
        {'player_class': 'Assassin', 'player_total_fcr': 102},
        ('330:0', '334:0'),
    ),
    (
        'meteor-sorceress',
        2,
        'harlequin',
        'Shako',
        'Harlequin Crest',
        FIRE,
        THUNDER,
        ((127, 0, 2), (80, 0, 65), (329, 0, 5), (333, 0, 5)),
        {'player_class': 'Sorceress', 'player_total_fcr': 105, 'player_total_fhr': 60},
        ('329:0', '333:0'),
    ),
    (
        'meteor-sorceress',
        4,
        'vipermagi',
        'Serpentskin Armor',
        'Skin of the Vipermagi',
        RESIST,
        SocketItem('Jewel', ((99, 0, 7), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 14)), True),
        ((105, 0, 30), (127, 0, 1), (39, 0, 35), (41, 0, 35), (43, 0, 35), (45, 0, 35), (99, 0, 7)),
        {'player_class': 'Sorceress', 'player_total_fcr': 105, 'player_total_fhr': 86},
        ('99:0', '39:0', '45:0'),
    ),
)


def cases():
    for build, variant, suffix, base, name, child, wrong_child, stats, context, keys in SPECS:
        role = f'{build}-{variant}-{suffix}-socketed'
        config = role + '-stats'
        item = Item(base, 'unique', name, stats, sockets=1, socket_contents='filled', socket_items=(child,))
        examples = [
            ('ready-minimum-native', item, context, 'positive'),
            ('wrong-child', replace(item, socket_items=(wrong_child,)), context, 'negative'),
            ('empty-socket', replace(item, socket_contents='empty', socket_items=()), context, 'negative'),
            ('unread-child', replace(item, socket_items=()), context, 'unknown'),
            ('partial-child', replace(item, socket_items=(replace(child, complete=False),)), context, 'unknown'),
            ('ethereal-player', replace(item, ethereal=True), context, 'negative'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('below-fcr', item, {**context, 'player_total_fcr': context['player_total_fcr'] - 1}, 'negative'),
            ('unknown-fcr', item, {k: v for k, v in context.items() if k != 'player_total_fcr'}, 'unknown'),
        ]
        if suffix == 'vipermagi':
            examples.append(('upgraded-armor', replace(item, base='Wyrmhide'), context, 'positive'))
        if 'player_total_fhr' in context:
            examples.extend(
                [
                    ('below-fhr', item, {**context, 'player_total_fhr': context['player_total_fhr'] - 1}, 'negative'),
                    ('unknown-fhr', item, {k: v for k, v in context.items() if k != 'player_total_fhr'}, 'unknown'),
                ]
            )
        for label, candidate, loadout, scenario in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                ),
                'trade_tier': IsPartialDict(status='reviewed'),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'caster-socketed/{role}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (config,),
                report_contains=(name, 'Trade tier:'),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',),
            )


CASES = tuple(cases())
