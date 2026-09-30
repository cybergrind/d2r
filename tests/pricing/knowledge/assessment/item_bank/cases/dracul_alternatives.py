"""Life Tap supports Smite; ordinary life leech must not acquire that role."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


MINIMUM = ((16, 0, 90), (60, 0, 7), (135, 0, 25), (198, 5258, 5), (86, 0, 5), (0, 0, 10))
MAXIMUM = ((16, 0, 120), (60, 0, 10), (135, 0, 25), (198, 5258, 5), (86, 0, 10), (0, 0, 15))


def cases():
    for build, klass, slot in (
        ('dragon-talon-assassin', 'Assassin', 0),
        ('dream-paladin', 'Paladin', 2),
        ('smite-paladin', 'Paladin', 1),
    ):
        role = build + '-dracul-s-grasp-dracul-alternative'
        config = role + '-stats'
        item = Item('Vampirebone Gloves', 'unique', "Dracul's Grasp", MINIMUM)
        context = {'player_class': klass}
        for label, candidate, loadout, truth in (
            ('minimum', item, context, 'true'),
            ('maximum', replace(item, raw_stats=MAXIMUM), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                keys = ('198:5258', '135:0', '0:0', '86:0', *(() if build == 'smite-paladin' else ('60:0',)))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'dracul-alternative/{build}/{label}',
                item=candidate,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations={'60:0': (config,)} if build == 'smite-paladin' else {},
                report_contains=(
                    "Dracul's Grasp",
                    'Trade tier:',
                    '5% Chance to cast level 10 Life Tap on striking',
                    '25% Chance of Open Wounds',
                    *(('(7-10%)', '(10-15)') if candidate.socket_contents == 'empty' else ()),
                )
                if candidate.identified
                else (),
                report_absent=('(7-10%)', '(10-15)') if label == 'unknown-sockets' else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Gloves/{slot}',
                    'third-parties/d2data/json/uniqueitems.json:/364',
                ),
            )


CASES = tuple(cases())
