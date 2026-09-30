"""Standalone Trang pieces do not establish companions or full-set effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ENTRIES = (
    (
        'poison-nova-necromancer-trang-oul-s-guise-equipment-tail-alternative',
        Item(
            'Bone Visage',
            'set',
            "Trang-Oul's Guise",
            ((31, 0, 180), (99, 0, 25), (78, 0, 20), (9, 0, 150 * 256), (74, 0, 5)),
            named_table_id=85,
        ),
        None,
        ('99:0', '9:0', '74:0'),
        ('188:18',),
        '/poison-nova-necromancer/slots/Helmets/7',
        ('+150 to Mana', '25% Faster Hit Recovery'),
    ),
    (
        'poison-nova-necromancer-trang-oul-s-scales-equipment-tail-alternative',
        Item(
            'Chaos Armor',
            'set',
            "Trang-Oul's Scales",
            ((91, 0, -40), (32, 0, 100), (45, 0, 40), (188, 18, 2), (96, 0, 40), (16, 0, 150)),
            named_table_id=86,
        ),
        'Shadow Plate',
        ('188:18', '96:0', '45:0', '32:0'),
        ('41:0', '36:0', '188:17'),
        '/poison-nova-necromancer/slots/Body Armor/4',
        ('40% Faster Run/Walk', 'Poison Resist +40%'),
    ),
    (
        'summoner-necromancer-guide-trang-oul-s-wing-named-shield-tail',
        Item(
            'Cantor Trophy',
            'set',
            "Trang-Oul's Wing",
            ((31, 0, 175), (0, 0, 25), (2, 0, 15), (39, 0, 38), (20, 0, 30), (45, 0, 40), (188, 17, 2)),
            named_table_id=87,
        ),
        'Succubus Skull',
        ('188:17', '31:0', '0:0', '2:0', '39:0', '45:0', '20:0'),
        ('188:18', '336:0', '74:0'),
        '/summoner-necromancer-guide/slots/Off-Hand/1',
        ('Fire Resist +38%', '(38-45%)'),
    ),
)


def cases():
    for role, item, upgraded, keys, excluded_keys, locator, report in ENTRIES:
        config = role + '-stats'
        context = {'player_class': 'Necromancer'}
        variants = [
            ('standalone', item, context, 'true'),
            ('open-socket', replace(item, sockets=1, raw_stats=(*item.raw_stats, (194, 0, 1))), context, 'true'),
            ('two-sockets', replace(item, sockets=2, raw_stats=(*item.raw_stats, (194, 0, 2))), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('invalid-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
        ]
        if upgraded:
            upgraded_stats = tuple((stat, layer, 225 if stat == 31 else value) for stat, layer, value in item.raw_stats)
            variants.append(('upgraded', replace(item, base=upgraded, raw_stats=upgraded_stats), context, 'true'))
        if item.named_table_id in (85, 87):
            stat, maximum = (31, 257) if item.named_table_id == 85 else (39, 45)
            max_stats = tuple((s, layer, maximum if s == stat else value) for s, layer, value in item.raw_stats)
            variants.append(('maximum-roll', replace(item, raw_stats=max_stats), context, 'true'))
        for label, specimen, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'trang-standalone-uses/{item.named_table_id}/{label}',
                item=specimen,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(excluded_keys, (config,)),
                report_contains=(item.name, 'Trade tier:', *report) if active and label == 'standalone' else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    'third-parties/d2data/json/setitems.json:/' + item.name,
                ),
            )


CASES = tuple(cases())
