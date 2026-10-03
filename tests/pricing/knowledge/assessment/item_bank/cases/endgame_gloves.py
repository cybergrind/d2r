"""Named endgame gloves: wearer, loadout breakpoint and per-build stat benefits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


TRANG = Item(
    'Heavy Bracers',
    'set',
    "Trang-Oul's Claws",
    ((105, 0, 20), (43, 0, 30), (188, 16, 2), (332, 0, 25)),
    named_table_id=88,
)
HANDS = Item(
    'Bramble Mitts',
    'set',
    'Laying of Hands',
    ((93, 0, 20), (121, 0, 350), (39, 0, 50)),
    named_table_id=96,
)
MEMBERS = (
    ('summoner-necromancer-guide-2-trang-claws', TRANG, 'Necromancer', False, 75),
    ('summoner-necromancer-guide-1-trang-claws', TRANG, 'Necromancer', False, 125),
    ('poison-nova-necromancer-0-trang-claws', TRANG, 'Necromancer', True, 75),
    ('poison-nova-necromancer-1-trang-claws', TRANG, 'Necromancer', True, 125),
    ('poison-nova-necromancer-2-trang-claws', TRANG, 'Necromancer', True, 125),
    ('strafe-amazon-1-laying-hands', HANDS, 'Amazon', False, None),
)
TRANG_LINES = {
    '105:0': '+20% Faster Cast Rate',
    '43:0': 'Cold Resist +30%',
    '188:16': '+2 to Curses (Necromancer Only)',
    '332:0': '+25% to Poison Skill Damage',
}


def cases():
    for role, original, wearer, poison, breakpoint in MEMBERS:
        context = {'player_class': wearer, **({'player_total_fcr': breakpoint} if original == TRANG else {})}
        priorities = (
            {
                '105:0': 'desirable',
                '43:0': 'supporting',
                '188:16': 'supporting',
                **({'332:0': 'desirable'} if poison else {}),
            }
            if original == TRANG
            else {'93:0': 'desirable', '121:0': 'desirable', '39:0': 'supporting'}
        )
        scenarios = [
            ('positive', original, context, 'true'),
            ('wrong-class', original, {**context, 'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', original, {**context, 'player_class': None}, 'unknown'),
            ('impossible-ethereal', replace(original, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
            ('uncaptured-stats', replace(original, raw_stats=()), context, 'true'),
        ]
        if original == TRANG:
            scenarios += [
                ('below-breakpoint', original, {**context, 'player_total_fcr': breakpoint - 1}, 'false'),
                ('above-breakpoint', original, {**context, 'player_total_fcr': breakpoint + 1}, 'true'),
                ('unknown-breakpoint', original, {'player_class': wearer}, 'unknown'),
                ('gloves-not-whole-loadout', original, {**context, 'player_total_fcr': 20}, 'false'),
            ]
        for key in priorities:
            stat, layer = map(int, key.split(':'))
            scenarios.append(
                (
                    'missing-' + key,
                    replace(original, raw_stats=tuple(s for s in original.raw_stats if s[:2] != (stat, layer))),
                    context,
                    'true',
                )
            )
        for label, item, loadout, truth in scenarios:
            config = role + '-stats'
            captured = {f'{stat}:{layer}' for stat, layer, _ in item.raw_stats}
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(
                                contributions=Contains(
                                    IsPartialDict(
                                        configuration_id=config,
                                        role_id=role,
                                        desirability=grade,
                                    )
                                )
                            )
                            for key, grade in priorities.items()
                            if key in captured
                        }
                    )
                )
            absent = {key: (config,) for key in priorities if key not in captured}
            if original == TRANG and not poison:
                absent['332:0'] = (config,)
            yield Case(
                id=f'endgame-gloves/{role}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario='unknown'
                if label.startswith(('unknown', 'uncaptured', 'missing'))
                else 'positive'
                if active
                else 'negative',
                absent_configurations=() if active else (config,),
                absent_stat_configurations=absent,
                report_contains=(
                    original.name,
                    'Trade tier:',
                    *(line for key, line in TRANG_LINES.items() if original == TRANG and key in captured),
                )
                if item.identified and item.ethereal is not True
                else (),
                report_absent=(
                    *(('Trade tier:',) if item.ethereal is True else ()),
                    *(line for key, line in TRANG_LINES.items() if original == TRANG and key not in captured),
                ),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/setitems.json'),
            )


CASES = tuple(cases())
