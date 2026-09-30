"""Explicit native boundaries for Ravenlore, Darkforce Spawn and Windforce build uses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'fissure-druid-ravenlore-equipment-tail-alternative',
        'Druid',
        'Sky Spirit',
        'Ravenlore',
        350,
        (
            (188, 42, 3),
            (333, 0, 10),
            (1, 0, 20),
            (16, 0, 120),
            (107, 221, 7),
            (39, 0, 15),
            (41, 0, 15),
            (43, 0, 15),
            (45, 0, 15),
        ),
        {333: 20, 1: 30, 16: 150, 39: 25, 41: 25, 43: 25, 45: 25},
        ('188:42', '333:0', '1:0', '39:0', '41:0', '43:0', '45:0'),
        '(10-20%)',
    ),
    (
        'poison-nova-necromancer-darkforce-spawn-equipment-tail-alternative',
        'Necromancer',
        'Bloodlord Skull',
        'Darkforce Spawn',
        330,
        ((188, 16, 1), (188, 17, 1), (188, 18, 1), (105, 0, 30), (77, 0, 10), (16, 0, 140)),
        {188: 3, 16: 180},
        ('188:16', '188:17', '188:18', '105:0', '77:0'),
        '(1-3)',
    ),
    (
        'strafe-amazon-windforce-weapon-tail-alternative',
        'Amazon',
        'Hydra Bow',
        'Windforce',
        266,
        (
            (17, 0, 250),
            (18, 0, 250),
            (218, 0, 25),
            (93, 0, 20),
            (62, 0, 6),
            (81, 0, 1),
            (0, 0, 10),
            (2, 0, 5),
            (28, 0, 30),
        ),
        {62: 8},
        ('17:0', '218:0', '93:0', '62:0', '81:0', '0:0', '2:0'),
        '(6-8%)',
    ),
)


def cases():
    for role, player, base, name, native_id, stats, high, keys, range_text in SPECS:
        config = role + '-stats'
        item = Item(base, 'unique', name, stats)
        context = {'player_class': player}
        rows = (
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((sid, layer, high.get(sid, value)) for sid, layer, value in stats)),
                context,
                'true',
            ),
            ('open-socket', replace(item, sockets=1), context, 'true'),
            ('too-many-sockets', replace(item, sockets=2), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        )
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'valuable-named-alternative/{name}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=(name, 'Trade tier:', range_text) if truth == 'true' else (name,),
                evidence=('pricing/data/wp-a-builds.json', f'third-parties/d2data/json/uniqueitems.json:/{native_id}'),
            )


CASES = tuple(cases())
