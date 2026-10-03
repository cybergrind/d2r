"""Armor-only Hustle effects, with player durability and mercenary skill boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('Barbarian', 'merc', ('double-throw-barbarian-guide',)),
    ('Paladin', 'merc', ('dream-paladin',)),
    ('Druid', 'merc', ('fissure-druid',)),
    ('Amazon', 'merc', ('lightning-fury-amazon-guide', 'lightning-strike-amazon')),
    ('Sorceress', 'merc', ('lightning-sorceress',)),
    ('Necromancer', 'merc', ('poison-nova-necromancer',)),
    ('Barbarian', 'player', ('double-throw-barbarian-guide',)),
    ('Paladin', 'player', ('smite-paladin',)),
    ('Paladin', 'zeal-merc', ('zeal-paladin',)),
)
KEYS = ('93:0', '96:0', '99:0', '39:0', '41:0', '43:0', '45:0')


def armor(quality):
    return Item(
        'Mage Plate',
        quality,
        'Hustle (armor)',
        (
            (93, 0, 40),
            (96, 0, 65),
            (99, 0, 20),
            (2, 0, 10),
            (97, 29, 6),
            (39, 0, 10),
            (41, 0, 10),
            (43, 0, 10),
            (45, 0, 10),
            (194, 0, 3),
        ),
        sockets=3,
        socket_contents='filled',
        runeword='Hustle (armor)',
        socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Ko Rune', 'Eld Rune')),
    )


def cases():
    for klass, side, builds in SPECS:
        player = side == 'player'
        zeal = side == 'zeal-merc'
        roles = (
            ('zeal-paladin-early-merc-hustle',)
            if zeal
            else tuple(
                build + ('-player-main-alternatives' if player else '-merc-early') + '-hustle-armor-alternative'
                for build in builds
            )
        )
        configs = tuple(role + '-stats' for role in roles)
        keys = KEYS + (('97:29',) if player else ('2:0',) if zeal else ())
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = armor(quality)
            examples = [
                ('native', item, context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false' if player else 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown' if player else 'true'),
                ('elite-base', replace(item, base='Dusk Shroud'), context, 'true'),
                ('insufficient-capacity', replace(item, base='Quilted Armor'), context, 'false'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
            ]
            if zeal:
                examples.extend(
                    [
                        ('frenzy-bearer', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'true'),
                        ('wrong-bearer', item, {**context, 'mercenary_type': 'Act 3 Fire'}, 'false'),
                        ('unknown-bearer', item, {'player_class': klass}, 'unknown'),
                    ]
                )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {
                    'roles': Contains(
                        *(
                            IsPartialDict(
                                id=role, side='player' if player else 'merc', rule_trace=IsPartialDict(truth=truth)
                            )
                            for role in roles
                        )
                    )
                }
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    configuration_ids=Contains(*configs),
                                    contributions=Contains(
                                        *(
                                            IsPartialDict(
                                                configuration_id=config,
                                                desirability='desirable'
                                                if zeal or key in ('93:0', '96:0')
                                                else 'supporting',
                                            )
                                            for config in configs
                                        )
                                    ),
                                )
                                for key in keys
                            }
                        )
                    )
                excluded = ('151:122', '198:16513', '60:0') + (() if player else ('97:29',))
                yield Case(
                    id=f'hustle-armor-choices/{klass}/{side}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    absent_stat_configurations=dict.fromkeys(excluded, configs),
                    report_contains=('Hustle', 'Shael, Ko, Eld', '40% Increased Attack Speed', '65% Faster Run/Walk')
                    if active
                    else (),
                    report_absent=('Fanaticism', 'Burst of Speed', 'Life stolen per hit'),
                    evidence=(
                        *(
                            (
                                'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/213',
                            )
                            if zeal
                            else tuple(
                                f'pricing/data/wp-a-builds.json:/{build}/'
                                + (
                                    f'slots/Body Armor/{2 if klass == "Barbarian" else 5}'
                                    if player
                                    else 'merc/Body Armor/early/2'
                                )
                                for build in builds
                            )
                        ),
                        'third-parties/d2data/json/runes.json:/Hustle (armor)',
                    ),
                )


CASES = tuple(cases())
