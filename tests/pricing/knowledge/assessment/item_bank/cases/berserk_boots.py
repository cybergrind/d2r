"""Berserk attack boots retain native proc chances across defense rolls/upgrades."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('goblin-toe', Item('Light Plated Boots', 'unique', 'Goblin Toe',
                       ((136, 0, 25), (34, 0, 1), (35, 0, 1), (16, 0, 50))),
     ('136:0', '34:0', '35:0'), ('Battle Boots', 'Mirrored Boots'), 60),
    ('gore-rider', Item('War Boots', 'unique', 'Gore Rider',
                       ((136, 0, 15), (135, 0, 10), (96, 0, 30), (141, 0, 15), (16, 0, 160))),
     ('136:0', '135:0', '96:0', '141:0'), ('Myrmidon Greaves',), 200),
)


def cases():
    context = {'player_class': 'Barbarian'}
    for slug, item, keys, upgrades, maximum in SPECS:
        role = 'berserk-barbarian-' + slug + '-boots-belts-alternative'
        rows = [
            ('minimum-defense', item, context, 'true'),
            ('maximum-defense', replace(item, raw_stats=tuple(
                (s, layer, maximum if s == 16 else v) for s, layer, v in item.raw_stats
            )), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('invalid-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        rows += [(base, replace(item, base=base), context, 'true') for base in upgrades]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict({
                    key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys
                }))
            yield Case(
                id=f'berserk/boots/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations={'16:0': (role + '-stats',)},
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=('pricing/data/wp-a-builds.json:/berserk-barbarian/slots/Boots',
                          'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
