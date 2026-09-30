"""Guide early Ground and Starter ethereal Crown Bulwark/Holy Freeze.

Native Non-Ladder recipes supply the independent roll examples. Exact Starter
placement is distinct from generic early elemental mitigation.
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'Ground',
        'ground-merc-early',
        'Bone Visage',
        False,
        ((41, 0, 40), (144, 0, 10), (76, 0, 5), (99, 0, 20), (16, 0, 75), (3, 0, 10)),
        ('41:0', '144:0', '76:0', '99:0'),
    ),
    (
        'Bulwark',
        '0-merc-bulwark-native',
        'Crown',
        True,
        ((60, 0, 4), (36, 0, 10), (76, 0, 5), (99, 0, 20), (16, 0, 75), (3, 0, 10), (34, 0, 7), (74, 0, 30)),
        ('60:0', '36:0', '76:0', '99:0'),
    ),
)


def cases():
    context = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Holy Freeze'}
    for word, suffix, base, ethereal, raw, keys in EXAMPLES:
        role = 'blessed-hammer-paladin-' + suffix
        config = role + '-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(base, quality, word, raw, ethereal=ethereal, sockets=3, socket_contents='filled', runeword=word)
            maximum = {41: 60, 144: 15, 16: 100} if word == 'Ground' else {60: 6, 36: 15, 16: 100}
            rows = [
                ('minimum', item, context, 'true'),
                (
                    'maximum',
                    replace(item, raw_stats=tuple((s, p, maximum.get(s, v)) for s, p, v in raw)),
                    context,
                    'true',
                ),
                ('nonethereal', replace(item, ethereal=False), context, 'true' if word == 'Ground' else 'false'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true' if word == 'Ground' else 'unknown'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('two-sockets', replace(item, sockets=2), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                (
                    'other-aura',
                    item,
                    {**context, 'mercenary_type': 'Act 2 Might'},
                    'true' if word == 'Ground' else 'false',
                ),
                ('unknown-merc', item, {'player_class': 'Paladin'}, 'true' if word == 'Ground' else 'unknown'),
                ('other-base', replace(item, base='Mask'), context, 'true' if word == 'Ground' else 'false'),
                ('insufficient-capacity', replace(item, base='Cap'), context, 'false'),
            ]
            for label, candidate, loadout, truth in rows:
                expected = {
                    'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'hammer/merc-helms/{word.lower()}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations={'3:0': (config,)},
                    report_contains=(word,),
                    evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
