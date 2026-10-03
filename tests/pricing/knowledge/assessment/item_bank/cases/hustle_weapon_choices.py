"""Separate existing Hustle weapon utility from armor and temporary prebuff assumptions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.hustle_armor_choices import armor
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', 'Act 2 Might', 'Thresher', ('early', 'mid'), 0),
    ('dream-paladin', 'Paladin', 'Act 2 Might', 'Thresher', ('early',), 0),
    ('lightning-fury-amazon-guide', 'Amazon', 'Act 2 Might', 'Thresher', ('early', 'mid'), 1),
    ('lightning-strike-amazon', 'Amazon', 'Act 2 Holy Freeze', 'Thresher', ('early', 'mid'), 1),
    ('poison-nova-necromancer', 'Necromancer', 'Act 2 Might', 'Thresher', ('mid',), 1),
    ('double-throw-barbarian-guide', 'Barbarian', None, 'Phase Blade', ('main-alternatives',), 6),
    ('strafe-amazon', 'Amazon', None, "Hunter's Bow", ('main-alternatives',), 0),
)
PROC = '198:16513'
AURA = '151:122'


def weapon(quality, base, damage=180):
    return Item(
        base,
        quality,
        'Hustle (weapon)',
        (
            (17, 0, damage),
            (18, 0, damage),
            (93, 0, 30),
            (151, 122, 1),
            (198, 16513, 5),
            (2, 0, 10),
            (122, 0, 75),
            (124, 0, 50),
            (194, 0, 3),
        ),
        sockets=3,
        socket_contents='filled',
        runeword='Hustle (weapon)',
        socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Ko Rune', 'Eld Rune')),
    )


def cases():
    for build, klass, merc, base, stages, index in SPECS:
        side = 'merc' if merc else 'player'
        roles = tuple(f'{build}-{side}-{stage}-hustle-weapon-alternative' for stage in stages)
        configs = tuple(role + '-stats' for role in roles)
        keys = ('17:0', '18:0', '93:0', AURA, PROC) if merc else ('93:0', PROC)
        context = {'player_class': klass, **({'mercenary_type': merc} if merc else {})}
        for quality in ('normal', 'superior', 'low_quality'):
            item = weapon(quality, base)
            examples = [
                ('native-minimum', item, context, 'true'),
                ('native-maximum', weapon(quality, base, 200), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'true' if merc else 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true' if merc else 'unknown'),
                ('wrong-class', item, {**context, 'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('armor-variant', armor(quality), context, 'false'),
                (
                    'wrong-weapon-type',
                    replace(item, base='Thresher' if not merc else 'Crystal Sword'),
                    context,
                    'false',
                ),
            ]
            if merc:
                examples.extend(
                    [
                        ('wrong-bearer', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
                        ('unknown-bearer', item, {'player_class': klass}, 'unknown'),
                    ]
                )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {}
                if label not in ('armor-variant', 'wrong-weapon-type'):
                    expected['roles'] = Contains(
                        *(
                            IsPartialDict(
                                id=role,
                                side=side,
                                rule_trace=IsPartialDict(truth=truth),
                                missing=Contains(
                                    'Burst of Speed requires a successful on-striking proc and lasts temporarily; '
                                    'it is not permanent item IAS. The proc buffs the wielder, '
                                    'not the player through a mercenary.',
                                    'Fanaticism is supplied only while this weapon is active '
                                    'and recipients are in range; '
                                    'swapping away removes its aura even while a proc buff lasts.',
                                ),
                            )
                            for role in roles
                        )
                    )
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
                                                desirability=(
                                                    'desirable' if key in ('17:0', '18:0', AURA) else 'supporting'
                                                )
                                                if merc
                                                else ('desirable' if key == PROC else 'supporting'),
                                            )
                                            for config in configs
                                        )
                                    ),
                                )
                                for key in keys
                            }
                        )
                    )
                excluded = ('60:0', '97:29') + (() if merc else ('17:0', '18:0', AURA))
                yield Case(
                    id=f'hustle-weapon-choices/{build}/{side}/{quality}/{label}',
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
                    report_contains=('Hustle', 'Shael, Ko, Eld', 'Burst of Speed') if active else (),
                    report_absent=('Life stolen per hit',),
                    evidence=(
                        *(
                            f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/{stage}/{index}'
                            if merc
                            else f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon-Swap/{index}'
                            for stage in stages
                        ),
                        'third-parties/d2data/json/runes.json:/Hustle (weapon)',
                    ),
                )


CASES = tuple(cases())
