"""Fire-defense ring utility and separate Gold Find priority."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Paladin': (('dream-paladin', 8), ('fist-of-the-heavens-paladin', 4), ('smite-paladin', 3)),
    'Druid': (('fissure-druid', 6),),
    'Barbarian': (('gold-find-barbarian', 0),),
    'Amazon': (('lightning-fury-amazon-guide', 5), ('lightning-strike-amazon', 9)),
    'Sorceress': (('lightning-sorceress', 9), ('meteor-sorceress', 3)),
}


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-dwarf-star-defensive-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = Item(
            'Ring',
            'unique',
            'Dwarf Star',
            ((79, 0, 100), (11, 0, 40 << 8), (28, 0, 15), (7, 0, 40 << 8), (35, 0, 12), (142, 0, 15)),
            complete=True,
        )
        context = {'player_class': player_class}
        examples = (
            ('minimum', item, context, 'true'),
            (
                'perfect-mdr',
                replace(item, raw_stats=tuple((s, layer, 15 if s == 35 else v) for s, layer, v in item.raw_stats)),
                context,
                'true',
            ),
            (
                'unknown-mdr',
                replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 35), complete=False),
                context,
                'true',
            ),
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
                keys = ['142:0', '7:0']
                if label != 'unknown-mdr':
                    keys.append('35:0')
                if player_class == 'Barbarian':
                    keys.append('79:0')
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if label in ('minimum', 'perfect-mdr'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=35, layer=0),
                            roll_range=IsPartialDict(min=12, max=15),
                            roll_quality='perfect' if label == 'perfect-mdr' else 'low',
                        )
                    )
                )
            absent = dict.fromkeys(('11:0', '28:0'), configs)
            if player_class != 'Barbarian':
                absent['79:0'] = configs
            if label == 'unknown-mdr':
                absent['35:0'] = configs
            yield Case(
                id=f'dwarf-star-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unknown-mdr'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Dwarf Star', 'Trade tier:') if truth == 'true' else ('Ring',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/274',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Rings/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
