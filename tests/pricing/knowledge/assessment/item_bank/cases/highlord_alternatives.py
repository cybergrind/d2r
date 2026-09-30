"""Highlord skill/IAS utility and level-scaled physical Deadly Strike boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('double-throw-barbarian-guide', 0),),
    'Assassin': (('dragon-talon-assassin', 3),),
    'Paladin': (('dream-paladin', 0),),
    'Sorceress': (('enchant-sorceress', 3),),
    'Amazon': (('lightning-fury-amazon-guide', 0), ('lightning-strike-amazon', 0), ('strafe-amazon', 1)),
}


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-highlord-s-wrath-jewelry-casting-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = Item(
            'Amulet',
            'unique',
            "Highlord's Wrath",
            ((41, 0, 35), (50, 0, 1), (51, 0, 30), (93, 0, 20), (127, 0, 1), (250, 0, 3), (128, 0, 15)),
            complete=True,
        )
        context = {'player_class': player_class}
        examples = (
            ('level65', replace(item, viewer_level=65), context, 'true'),
            ('level80', item, context, 'true'),
            ('level99', replace(item, viewer_level=99), context, 'true'),
            ('unknown-level', replace(item, viewer_level=None), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                keys = ['127:0', '93:0', '41:0']
                if player_class != 'Assassin' and label != 'unknown-level':
                    keys.append('250:0')
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
                if label != 'unknown-level':
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict({'250:0': IsPartialDict(value=candidate.viewer_level * 3 // 8)})
                    )
            absent = dict.fromkeys(('50:0', '51:0', '128:0'), configs)
            if player_class == 'Assassin' or label == 'unknown-level':
                absent['250:0'] = configs
            yield Case(
                id=f'highlord-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unknown-level'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else ('Amulet',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/276',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Amulets/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
