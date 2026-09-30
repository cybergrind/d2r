"""Trek utility and independent rolls, with explicit ethereal repair requirements."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Warlock': (('echoing-strike-warlock-guide', 1), ('fire-warlock-guide', 2), ('mirrored-blades-warlock-guide', 1)),
    'Sorceress': (
        ('enchant-sorceress', 3),
        ('lightning-sorceress', 2),
        ('meteor-sorceress', 1),
        ('nova-sorceress-guide', 2),
    ),
    'Druid': (('fissure-druid', 3),),
    'Paladin': (('fist-of-the-heavens-paladin', 1), ('smite-paladin', 2)),
    'Assassin': (('lightning-sentry-assassin', 4), ('wake-of-fire-assassin', 4)),
    'Necromancer': (('poison-nova-necromancer', 3),),
    'Amazon': (('strafe-amazon', 1),),
}
RANGES = {16: (140, 170), 0: (10, 15), 3: (10, 15), 45: (40, 70)}


def boots(defense=140, strength=10, vitality=10, poison=40):
    return Item(
        'Scarabshell Boots',
        'unique',
        'Sandstorm Trek',
        (
            (16, 0, defense),
            (96, 0, 20),
            (99, 0, 20),
            (242, 0, 8),
            (154, 0, 50),
            (45, 0, poison),
            (252, 0, 5),
            (0, 0, strength),
            (3, 0, vitality),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-trek-boots-alternative' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        item = boots()
        no_repair = tuple(r for r in item.raw_stats if r[0] != 252)
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', boots(170, 15, 15, 70), context, 'true'),
            ('perfect-defense-only', boots(170, 10, 10, 40), context, 'true'),
            ('perfect-strength-only', boots(140, 15, 10, 40), context, 'true'),
            ('perfect-vitality-only', boots(140, 10, 15, 40), context, 'true'),
            ('perfect-poison-only', boots(140, 10, 10, 70), context, 'true'),
            ('ethereal-repair', replace(item, ethereal=True), context, 'true'),
            ('ethereal-no-repair', replace(item, ethereal=True, raw_stats=no_repair), context, 'false'),
            (
                'ethereal-unknown-repair',
                replace(item, ethereal=True, raw_stats=no_repair, complete=False),
                context,
                'unknown',
            ),
            ('noneth-unknown-repair', replace(item, raw_stats=no_repair, complete=False), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
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
                            for key in ('96:0', '99:0', '0:0', '3:0', '45:0')
                        }
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if label == 'minimum' or label.startswith('perfect'):
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=RANGES[stat][0], max=RANGES[stat][1]),
                                roll_quality='perfect' if value == RANGES[stat][1] else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in RANGES
                        )
                    )
                )
            yield Case(
                id=f'trek-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=dict.fromkeys(('16:0', '242:0', '154:0'), configs),
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Sandstorm Trek', 'Trade tier:') if truth == 'true' else ('Scarabshell Boots',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/369',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Boots/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
