"""Hustle Act2 and the explicit Chaos Prep Act5 Bash Lawbringer setup."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('merc-mid-hustle-weapon-alternative', 'Act 2 Might',
     Item('Thresher', 'normal', 'Hustle (weapon)',
          ((17, 0, 180), (18, 0, 180), (93, 0, 30), (151, 122, 1), (198, 16513, 5)),
          sockets=3, socket_contents='filled', runeword='Hustle (weapon)'),
     ('17:0', '93:0', '151:122', '198:16513'), {17: 200, 18: 200}),
    ('lawbringer-chaos-prep-act-5-bash-merc-sword-tail', 'Act 5 Bash',
     Item('Legend Sword', 'normal', 'Lawbringer',
          ((151, 119, 16), (198, 5583, 20), (60, 0, 7), (32, 0, 200), (2, 0, 10),
           (116, 0, 50), (48, 0, 150), (49, 0, 210), (54, 0, 130), (55, 0, 180)),
          ethereal=True, sockets=3, socket_contents='filled', runeword='Lawbringer'),
     ('151:119', '198:5583', '60:0', '32:0', '2:0', '116:0', '48:0', '49:0', '54:0', '55:0'),
     {151: 18, 32: 250}),
)


def cases():
    for slug, merc, original, keys, maxima in SPECS:
        role = 'berserk-barbarian-' + slug
        context = {'player_class': 'Barbarian', 'mercenary_type': merc}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(original, rarity=quality)
            for label, candidate, loadout, truth in (
                ('minimum', item, context, 'true'),
                ('maximum', replace(item, raw_stats=tuple(
                    (s, layer, maxima.get(s, v)) for s, layer, v in item.raw_stats
                )), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('nonethereal', replace(item, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=2), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {'mercenary_type': merc}, 'unknown'),
                ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
                ('unknown-merc', item, {'player_class': 'Barbarian'}, 'unknown'),
            ):
                expected = {
                    'roles': Contains(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)))
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict({
                        key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys
                    }))
                yield Case(
                    id=f'berserk/merc-weapon-tail/{slug}/{quality}/{label}',
                    item=candidate, context=loadout, expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    report_contains=(item.name,),
                    evidence=('pricing/data/wp-a-builds.json:/berserk-barbarian',
                              'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
