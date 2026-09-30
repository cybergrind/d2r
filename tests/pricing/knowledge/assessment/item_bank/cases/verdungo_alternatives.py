"""Defensive belt priorities and independently graded Verdungo rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('double-throw-barbarian-guide', 5),),
    'Assassin': (('dragon-talon-assassin', 2), ('lightning-sentry-assassin', 3), ('wake-of-fire-assassin', 3)),
    'Paladin': (('dream-paladin', 2), ('fist-of-the-heavens-paladin', 1), ('smite-paladin', 3)),
    'Druid': (('fissure-druid', 1),),
    'Amazon': (('lightning-fury-amazon-guide', 4), ('lightning-strike-amazon', 2)),
    'Sorceress': (('lightning-sorceress', 2), ('meteor-sorceress', 2), ('nova-sorceress-guide', 3)),
    'Necromancer': (('poison-nova-necromancer', 4),),
}
RANGES = {16: (90, 140), 3: (30, 40), 11: (100, 120), 36: (10, 15), 74: (10, 13)}


def belt(defense=90, vitality=30, stamina=100, reduction=10, regeneration=10):
    return Item(
        'Mithril Coil',
        'unique',
        "Verdungo's Hearty Cord",
        (
            (16, 0, defense),
            (3, 0, vitality),
            (11, 0, stamina << 8),
            (99, 0, 10),
            (36, 0, reduction),
            (74, 0, regeneration),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-verdungo-s-hearty-cord-defensive-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = belt()
        context = {'player_class': player_class}
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', belt(140, 40, 120, 15, 13), context, 'true'),
            ('perfect-defense-only', belt(defense=140), context, 'true'),
            ('perfect-vitality-only', belt(vitality=40), context, 'true'),
            ('perfect-reduction-only', belt(reduction=15), context, 'true'),
            ('perfect-regeneration-only', belt(regeneration=13), context, 'true'),
            ('perfect-stamina-only', belt(stamina=120), context, 'true'),
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
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in ('36:0', '3:0', '99:0', '74:0')
                        }
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=RANGES[stat][0], max=RANGES[stat][1]),
                                roll_quality='perfect'
                                if (raw >> 8 if stat == 11 else raw) == RANGES[stat][1]
                                else 'low',
                            )
                            for stat, _, raw in candidate.raw_stats
                            if stat in RANGES
                        )
                    )
                )
            yield Case(
                id=f'verdungo-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(('16:0', '11:0'), configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else ('Mithril Coil',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/376',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Belts/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
