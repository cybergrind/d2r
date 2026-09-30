"""The Tri-Brid mercenary's Lawbringer does not confer its weapon effects on FoH."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fist-of-the-heavens-paladin-lawbringer-tri-brid-act-5-frenzy-merc-sword-tail'
CONFIG = ROLE + '-stats'
SOURCE = 'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/3/merc'


def lawbringer(quality, aura=16, missile_defense=200):
    return Item(
        'Phase Blade',
        quality,
        'Lawbringer',
        (
            (151, 119, aura),
            (198, 5583, 20),
            (60, 0, 7),
            (32, 0, missile_defense),
            (2, 0, 10),
            (116, 0, 50),
            (48, 0, 150),
            (49, 0, 210),
            (54, 0, 130),
            (55, 0, 180),
            (108, 0, 1),
            (79, 0, 75),
            (194, 0, 3),
        ),
        runeword='Lawbringer',
        sockets=3,
        socket_contents='filled',
        socket_items=tuple(SocketItem(name) for name in ('Amn Rune', 'Lem Rune', 'Ko Rune')),
    )


def cases():
    context = {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy', 'mercenary_items': []}
    for quality in ('normal', 'superior', 'low_quality'):
        item = lawbringer(quality)
        examples = [
            (f'rolls-{aura}-{defense}', lawbringer(quality, aura, defense), context, 'true')
            for aura in (16, 17, 18)
            for defense in (200, 250)
        ]
        examples += [
            ('unknown-other-hand', item, {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            # Do not fabricate an ethereal Phase Blade. A real ethereal Cryptic
            # Sword fits Frenzy generally but not this exact source configuration.
            ('different-ethereal-sword', replace(item, base='Cryptic Sword', ethereal=True), context, 'false'),
            ('two-handed-sword', replace(item, base='Legend Sword'), context, 'false'),
            ('bash-mercenary', item, {**context, 'mercenary_type': 'Act 5 Bash'}, 'false'),
            ('unknown-mercenary', item, {'player_class': 'Paladin'}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {'mercenary_type': 'Act 5 Frenzy'}, 'unknown'),
            ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ]
        for label, candidate, loadout, truth in examples:
            active = truth == 'true'
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=ROLE,
                        side='merc',
                        rule_trace=IsPartialDict(truth=truth),
                    )
                )
            }
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                configuration_ids=Contains(CONFIG),
                                contributions=Contains(
                                    IsPartialDict(
                                        configuration_id=CONFIG,
                                        role_id=ROLE,
                                        desirability=grade,
                                    )
                                ),
                            )
                            for key, grade in (
                                ('151:119', 'desirable'),
                                ('198:5583', 'desirable'),
                                *(
                                    (key, 'supporting')
                                    for key in ('60:0', '32:0', '2:0', '116:0', '48:0', '49:0', '54:0', '55:0')
                                ),
                            )
                        }
                    )
                )
            yield Case(
                id=f'foh-lawbringer/{quality}/{label}',
                item=candidate,
                context=loadout,
                covers=(ROLE,),
                scenario='unknown'
                if label.startswith('unknown-') and not active
                else 'positive'
                if active
                else 'negative',
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_configurations=() if active else (CONFIG,),
                absent_annotations=('93:0', '105:0', '17:0', '18:0'),
                report_contains=(
                    'Lawbringer',
                    'Amn, Lem, Ko',
                    'Sanctuary Aura',
                    '20% Chance to cast level 15 Decrepify on striking',
                    '7% Life stolen per hit',
                    'Slain Monsters Rest in Peace',
                )
                if active
                else (),
                evidence=(
                    SOURCE + '/Weapon/0',
                    SOURCE + '/type',
                    'third-parties/d2data/json/runes.json:/Lawbringer',
                    'third-parties/d2data/json/gems.json:/r11',
                    'third-parties/d2data/json/gems.json:/r20',
                    'third-parties/d2data/json/gems.json:/r18',
                    'third-parties/d2data/json/itemstatcost.json:/item_restinpeace',
                ),
            )


CASES = tuple(cases())
