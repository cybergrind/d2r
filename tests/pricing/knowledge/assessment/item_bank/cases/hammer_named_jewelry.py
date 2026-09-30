"""Standalone Hammerdin amulets and Nature's Peace from guide slot alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'seraph-s-hymn',
        Item(
            'Amulet',
            'unique',
            "Seraph's Hymn",
            ((127, 0, 2), (188, 26, 1), (121, 0, 25), (122, 0, 25), (123, 0, 150), (124, 0, 150)),
        ),
        ('127:0',),
        ('121:0', '122:0', '123:0', '124:0'),
        {188: 2, 121: 50, 122: 50, 123: 250, 124: 250},
    ),
    (
        'telling-of-beads',
        Item('Amulet', 'set', 'Telling of Beads', ((127, 0, 1), (43, 0, 18), (45, 0, 35), (78, 0, 8))),
        ('127:0', '43:0', '45:0'),
        ('78:0',),
        {45: 50, 78: 10},
    ),
    (
        'nature-s-peace',
        Item(
            'Ring',
            'unique',
            "Nature's Peace",
            ((108, 0, 1), (117, 0, 1), (34, 0, 7), (45, 0, 20), (204, 226 * 64 + 5, (27 << 8) | 27)),
        ),
        ('108:0', '34:0', '45:0'),
        ('204:14469',),
        {34: 11, 45: 30},
    ),
)


def cases():
    context = {'player_class': 'Paladin', 'player_items': []}
    for slug, item, keys, excluded, maxima in SPECS:
        role = 'blessed-hammer-paladin-' + slug + '-jewelry-casting-alternative'
        config = role + '-stats'
        rows = [
            ('minimum-alone', item, context, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, p, maxima.get(s, v)) for s, p, v in item.raw_stats)),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('invalid-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ]
        if slug == 'nature-s-peace':
            rows += [
                (
                    'depleted-oak',
                    replace(item, raw_stats=(*item.raw_stats[:-1], (204, 14469, 27 << 8))),
                    context,
                    'true',
                ),
                ('unread-oak', replace(item, raw_stats=item.raw_stats[:-1]), context, 'true'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'hammer/named-jewelry/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else (item.base,),
                evidence=(
                    'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                    'third-parties/d2data/json/setitems.json',
                ),
            )


CASES = tuple(cases())
