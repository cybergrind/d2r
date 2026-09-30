"""Reviewed melee words preserve native recipes, rolls and Smite-specific utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


GRIEF = ((111, 0, 340), (93, 0, 30), (141, 0, 20), (115, 0, 1), (116, 0, 25), (243, 0, 15), (86, 0, 10))
LAST_WISH = ((17, 0, 330), (18, 0, 330), (136, 0, 60), (151, 98, 17), (198, 5266, 10), (201, 17099, 6), (115, 0, 1))
SPECS = (
    ('smite-paladin', 'Paladin', 'Grief', GRIEF, ('111:0', '93:0'), ('141:0', '115:0', '116:0')),
    ('dream-paladin', 'Paladin', 'Grief', GRIEF, ('111:0', '93:0', '141:0', '115:0', '116:0'), ()),
    ('gold-find-barbarian', 'Barbarian', 'Grief', GRIEF, ('111:0', '93:0', '141:0', '115:0', '116:0'), ()),
    (
        'smite-paladin',
        'Paladin',
        'Last Wish',
        LAST_WISH,
        ('136:0', '151:98', '198:5266', '201:17099'),
        ('17:0', '18:0', '115:0'),
    ),
    (
        'dream-paladin',
        'Paladin',
        'Last Wish',
        LAST_WISH,
        ('136:0', '151:98', '198:5266', '201:17099', '17:0', '115:0'),
        (),
    ),
)
RUNES = {'Grief': ('Eth', 'Tir', 'Lo', 'Mal', 'Ral'), 'Last Wish': ('Jah', 'Mal', 'Jah', 'Sur', 'Jah', 'Ber')}


def cases():
    for build, player_class, word, stats, keys, excluded_keys in SPECS:
        slug = word.lower().replace(' ', '-')
        role = f'{build}-{slug}-phase-blade-combat-word-alternative'
        config = role + '-stats'
        context = {'player_class': player_class}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Phase Blade',
                quality,
                word,
                (*stats, (194, 0, len(RUNES[word]))),
                sockets=len(RUNES[word]),
                socket_contents='filled',
                runeword=word,
                socket_items=tuple(SocketItem(name + ' Rune') for name in RUNES[word]),
            )
            native = NativeRunewordItem(**vars(item))
            high = tuple(
                (sid, layer, {111: 400, 93: 40, 136: 70, 17: 375, 18: 375}.get(sid, value))
                for sid, layer, value in item.raw_stats
            )
            rows = (
                ('minimum-roll', native, context, 'true'),
                ('maximum-roll', replace(native, raw_stats=high), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
                ('wrong-class', native, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'premium-phase-blade/{build}/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded_keys, (config,)),
                    report_contains=(
                        word,
                        'Sockets: ' + str(len(RUNES[word])) + ' — ' + ', '.join(RUNES[word]),
                        *(
                            ('(340-400)', '(30-40%)')
                            if word == 'Grief'
                            else ('(60-70%)', '(330-390%)' if quality == 'superior' else '(330-375%)')
                        ),
                    )
                    if truth == 'true'
                    else (word,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon',
                        f'third-parties/d2data/json/runes.json:/{word}',
                    ),
                )
            yield Case(
                id=f'premium-phase-blade/{build}/{slug}/{quality}/wrong-rune-order',
                item=replace(native, socket_items=tuple(reversed(native.socket_items))),
                context=context,
                expected={
                    'extraction': IsPartialDict(item=IsPartialDict(runeword=None)),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=(role,),
                scenario='negative',
                absent_roles=(role,),
                absent_configurations=(config,),
                report_contains=('Phase Blade',),
                evidence=(f'third-parties/d2data/json/runes.json:/{word}',),
            )


CASES = tuple(cases())
