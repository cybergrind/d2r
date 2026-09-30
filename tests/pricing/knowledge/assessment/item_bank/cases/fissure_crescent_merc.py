"""Crescent Moon on the Lightning Iron Wolf: wearer spell benefits, not melee bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'fissure-druid-crescent-moon-end-act-3-lightning-merc-sword-tail'
CONFIG = ROLE + '-stats'
MELEE_KEYS = ('17:0', '18:0', '93:0', '135:0', '115:0', '198:2701', '198:3409')


def moon(quality, damage=180, absorb=9):
    return Item(
        'Crystal Sword',
        quality,
        'Crescent Moon',
        (
            (334, 0, 35),
            (147, 0, absorb),
            (17, 0, damage),
            (18, 0, damage),
            (93, 0, 20),
            (135, 0, 25),
            (115, 0, 1),
            (138, 0, 2),
            (198, 42 * 64 + 13, 7),
            (198, 53 * 64 + 17, 10),
            (194, 0, 3),
        ),
        sockets=3,
        socket_contents='filled',
        runeword='Crescent Moon',
        socket_items=tuple(SocketItem(name) for name in ('Shael Rune', 'Um Rune', 'Tir Rune')),
    )


def cases():
    context = {'player_class': 'Druid', 'mercenary_type': 'Act 3 Lightning', 'mercenary_items': []}
    for quality in ('normal', 'superior', 'low_quality'):
        item = moon(quality)
        examples = [
            (f'rolls-{damage}-{absorb}', moon(quality, damage, absorb), context, 'true')
            for damage in (180, 220)
            for absorb in (9, 10, 11)
        ]
        examples += [
            ('ethereal-sword', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ('phase-blade', replace(item, base='Phase Blade'), context, 'true'),
            ('two-handed-sword', replace(item, base='Legend Sword'), context, 'false'),
            ('legal-word-wrong-bearer', replace(item, base='Thresher'), context, 'false'),
            ('wrong-element', item, {**context, 'mercenary_type': 'Act 3 Fire'}, 'false'),
            ('unknown-mercenary', item, {'player_class': 'Druid'}, 'unknown'),
            ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'false'),
            ('unknown-class', item, {'mercenary_type': 'Act 3 Lightning'}, 'unknown'),
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
            if label == 'legal-word-wrong-bearer':
                expected = {}  # Polearms never enter this sword-only role's candidate set.
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
                            for key, grade in (('334:0', 'desirable'), ('147:0', 'supporting'))
                        }
                    )
                )
            yield Case(
                id=f'fissure-crescent-merc/{quality}/{label}',
                item=candidate,
                context=loadout,
                covers=(ROLE,),
                scenario='unknown' if label.startswith('unknown-') else 'positive' if active else 'negative',
                expected={
                    'assessment': IsPartialDict(**expected),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                absent_configurations=() if active else (CONFIG,),
                absent_roles=(ROLE,) if label == 'legal-word-wrong-bearer' else (),
                absent_stat_configurations=dict.fromkeys((*MELEE_KEYS, '138:0'), (CONFIG,)),
                report_contains=(
                    'Crescent Moon',
                    'Shael, Um, Tir',
                    'Enemy Lightning Resistance',
                    'Magic Absorb',
                    '7% Chance to cast level 13 Static Field on striking',
                    '10% Chance to cast level 17 Chain Lightning on striking',
                )
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fissure-druid/merc/Weapon/end/2',
                    'pricing/data/wp-a-builds.json:/fissure-druid/merc/Mercenary Type/end/1',
                    'third-parties/d2data/json/runes.json:/Crescent Moon',
                    'third-parties/d2data/json/gems.json:/r13',
                    'third-parties/d2data/json/gems.json:/r22',
                    'third-parties/d2data/json/gems.json:/r03',
                    'third-parties/d2data/json/skills.json:/42',
                    'third-parties/d2data/json/skills.json:/53',
                ),
            )


CASES = tuple(cases())
