"""Reviewed War Pike mercenary alternative with native low/high rolls and bearer limits."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'berserk-barbarian-breath-of-the-dying-end-merc-weapon-alternative'


def cases():
    original = Item(
        'War Pike',
        'normal',
        'Breath of the Dying',
        (
            (17, 0, 350),
            (18, 0, 350),
            (93, 0, 60),
            (60, 0, 12),
            (62, 0, 7),
            (0, 0, 30),
            (1, 0, 30),
            (2, 0, 30),
            (3, 0, 30),
            (117, 0, 1),
            (122, 0, 200),
        ),
        ethereal=True,
        sockets=6,
        socket_contents='filled',
        runeword='Breath of the Dying',
    )
    context = {'player_class': 'Barbarian', 'mercenary_type': 'Act 2 Might'}
    for quality in ('normal', 'superior', 'low_quality'):
        item = replace(original, rarity=quality)
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(
                    item,
                    raw_stats=tuple((s, layer, {17: 400, 18: 400, 60: 15}.get(s, v)) for s, layer, v in item.raw_stats),
                ),
                context,
                'true',
            ),
            ('nonethereal', replace(item, ethereal=False), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ('uncited-polearm', replace(item, base='Giant Thresher'), context, 'absent'),
            ('insufficient-capacity', replace(item, base='Thresher'), context, 'absent'),
            ('incompatible-weapon', replace(item, base='Berserker Axe'), context, 'absent'),
            ('empty', replace(item, socket_contents='empty'), context, 'false'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
            ('wrong-count', replace(item, sockets=5), context, 'false'),
            ('unknown-count', replace(item, sockets=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
            ('unknown-merc', item, {'player_class': 'Barbarian'}, 'unknown'),
        ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=ROLE, side='merc', rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'absent':
                expected = {'roles': FunctionCheck(lambda rows: all(row['id'] != ROLE for row in rows))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                            for key in ('17:0', '93:0', '60:0', '0:0', '2:0', '122:0')
                        }
                    )
                )
            yield Case(
                id=f'berserk/botd-merc/{quality}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(ROLE,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown', 'absent': 'negative'}[truth],
                absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
                absent_stat_configurations=dict.fromkeys(('1:0', '3:0', '62:0', '117:0'), (ROLE + '-stats',)),
                report_contains=('Breath of the Dying',),
                evidence=(
                    'pricing/data/wp-a-builds.json:/berserk-barbarian/merc/Weapon/end/1',
                    'pricing/data/wp-a-variants/berserk-barbarian.json:/variants/1/merc/type',
                    'third-parties/d2data/json/runes.json:/Breath of the Dying',
                ),
            )


CASES = tuple(cases())
