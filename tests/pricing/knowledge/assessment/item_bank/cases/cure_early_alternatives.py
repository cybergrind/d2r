"""Native Cure alternatives retain cleansing utility across independently cited builds."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.cure_gear_alternatives import cure
from tests.pricing.knowledge.assessment.item_bank.models import Case


SOURCES = (
    (
        'Sorceress',
        (
            ('blizzard-sorceress', 3),
            ('enchant-sorceress', 6),
            ('lightning-sorceress', 6),
            ('meteor-sorceress', 3),
            ('nova-sorceress-guide', 4),
        ),
    ),
    ('Barbarian', (('double-throw-barbarian-guide', 5),)),
    ('Paladin', (('dream-paladin', 5), ('fist-of-the-heavens-paladin', 5))),
    ('Assassin', (('fire-blast-assassin', 4), ('lightning-sentry-assassin', 4))),
    ('Druid', (('fissure-druid', 6),)),
    ('Amazon', (('lightning-fury-amazon-guide', 6), ('lightning-strike-amazon', 6))),
    ('Necromancer', (('poison-nova-necromancer', 5), ('summoner-necromancer-guide', 5))),
)
KEYS = ('151:109', '45:0', '110:0', '76:0', '99:0')


def cases():
    for klass, sources in SOURCES:
        roles = tuple(build + '-early-merc-cure' for build, _ in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might', 'mercenary_items': []}
        for quality in ('normal', 'superior', 'low_quality'):
            item = cure(quality)
            examples = (
                ('native-minimum', item, context, 'true'),
                (
                    'native-maximum',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 60 if stat == 45 else 100 if stat == 16 else value)
                            for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                ('nonethereal', replace(item, ethereal=False), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('diadem', replace(item, base='Diadem'), context, 'true'),
                ('insufficient-base-capacity', replace(item, base='Cap'), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                ('no-mercenary-synergy-claim', item, {'player_class': klass}, 'true'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                (
                    'unread-cleansing',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 151)),
                    context,
                    'true',
                ),
            )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                keys = tuple(k for k in KEYS if not (label == 'unread-cleansing' and k == '151:109'))
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, side='merc', rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                        )
                    )
                absent = dict.fromkeys(('3:0', '74:0', '60:0'), configs)
                if label == 'unread-cleansing':
                    absent['151:109'] = configs
                yield Case(
                    id=f'cure-early-alternatives/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='unknown'
                    if truth == 'unknown' or label.startswith('unread-')
                    else 'positive'
                    if active
                    else 'negative',
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    absent_stat_configurations=absent,
                    report_contains=('Cure', 'Shael, Io, Tal') if active else (),
                    report_absent=('Replenish Life', 'Life stolen per hit'),
                    evidence=(
                        *(
                            f'pricing/data/wp-a-builds.json:/{build}/merc/Helmet/early/{index}'
                            for build, index in sources
                        ),
                        'third-parties/d2data/json/runes.json:/Cure',
                    ),
                )


CASES = tuple(cases())
