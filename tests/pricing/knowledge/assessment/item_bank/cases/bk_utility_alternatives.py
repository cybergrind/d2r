"""BK ring skill/life utility is independent of its physical life-steal roll."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Paladin': (('dream-paladin', 4), ('fist-of-the-heavens-paladin', 1), ('smite-paladin', 2)),
    'Warlock': (('echoing-strike-warlock-guide', 1), ('fire-warlock-guide', 1), ('mirrored-blades-warlock-guide', 1)),
    'Sorceress': (('enchant-sorceress', 2), ('lightning-sorceress', 6), ('meteor-sorceress', 1)),
    'Assassin': (('fire-blast-assassin', 2), ('lightning-sentry-assassin', 1), ('wake-of-fire-assassin', 1)),
    'Druid': (('fissure-druid', 3),),
    'Amazon': (('lightning-fury-amazon-guide', 3), ('lightning-strike-amazon', 7), ('strafe-amazon', 3)),
    'Necromancer': (('poison-nova-necromancer', 6),),
}


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-bk-ring-rings-utility-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = Item(
            'Ring',
            'unique',
            "Bul-Kathos' Wedding Band",
            ((127, 0, 1), (216, 0, 4 << 8), (60, 0, 3), (11, 0, 50 << 8)),
            complete=True,
        )
        context = {'player_class': player_class}
        examples = (
            ('minimum-leech', item, context, 'true'),
            (
                'perfect-leech',
                replace(item, raw_stats=((127, 0, 1), (216, 0, 4 << 8), (60, 0, 5), (11, 0, 50 << 8))),
                context,
                'true',
            ),
            ('level58', replace(item, viewer_level=58), context, 'true'),
            ('level99', replace(item, viewer_level=99), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('127:0', '216:0')}
                    )
                )
                expected['facts'] = IsPartialDict(
                    stats=IsPartialDict({'216:0': IsPartialDict(value=candidate.viewer_level // 2)})
                )
            result = {'assessment': IsPartialDict(**expected)}
            if label in ('minimum-leech', 'perfect-leech'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=60, layer=0),
                            roll_range=IsPartialDict(min=3, max=5),
                            roll_quality='perfect' if label == 'perfect-leech' else 'low',
                        )
                    )
                )
            yield Case(
                id=f'bk-utility/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(('60:0', '11:0'), configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else ('Ring',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/268',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Rings/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
