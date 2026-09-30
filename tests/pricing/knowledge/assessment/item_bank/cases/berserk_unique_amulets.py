"""Berserk amulet alternatives: attack scaling and intrinsic resistance utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GOLEM = 90 * 64 + 22
MAIDEN = 76 * 64 + 12
SPECS = (
    (
        'highlord-s-wrath',
        Item('Amulet', 'unique', "Highlord's Wrath", ((127, 0, 1), (93, 0, 20), (41, 0, 35), (250, 0, 3))),
        ('127:0', '93:0', '41:0', '250:0'),
    ),
    (
        'metalgrid',
        Item(
            'Amulet',
            'unique',
            'Metalgrid',
            (
                (31, 0, 300),
                (19, 0, 400),
                *((s, 0, 25) for s in (39, 41, 43, 45)),
                (204, GOLEM, (11 << 8) | 11),
                (204, MAIDEN, (20 << 8) | 20),
            ),
        ),
        ('31:0', '19:0', '39:0', '41:0', '43:0', '45:0'),
    ),
)


def cases():
    context = {'player_class': 'Barbarian'}
    for slug, item, keys in SPECS:
        role = 'berserk-barbarian-' + slug + '-jewelry-casting-alternative'
        rows = [
            ('native', item, context, 'true'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('invalid-sockets', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('invalid-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        if slug == 'metalgrid':
            rows += [
                (
                    'maximum',
                    replace(
                        item,
                        raw_stats=tuple(
                            (s, layer, {31: 350, 19: 450, 39: 35, 41: 35, 43: 35, 45: 35}.get(s, v))
                            for s, layer, v in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                (
                    'depleted',
                    replace(
                        item,
                        raw_stats=tuple((s, layer, (v >> 8) << 8 if s == 204 else v) for s, layer, v in item.raw_stats),
                    ),
                    context,
                    'true',
                ),
                (
                    'unread-charges',
                    replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 204)),
                    context,
                    'true',
                ),
            ]
        else:
            rows += [
                ('level-65', replace(item, viewer_level=65), context, 'true'),
                ('level-99', replace(item, viewer_level=99), context, 'true'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'berserk/unique-amulets/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys((f'204:{GOLEM}', f'204:{MAIDEN}'), (role + '-stats',)),
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/berserk-barbarian/slots/Amulets',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = tuple(cases())
