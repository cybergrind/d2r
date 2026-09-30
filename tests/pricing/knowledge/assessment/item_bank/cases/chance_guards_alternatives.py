"""Chance Guards farming utility across all three bases and explicit guide slots."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Barbarian': (('double-throw-barbarian-guide', 1), ('gold-find-barbarian', 0)),
    'Paladin': (('dream-paladin', 4), ('fist-of-the-heavens-paladin', 1)),
    'Warlock': (('echoing-strike-warlock-guide', 2), ('fire-warlock-guide', 2), ('mirrored-blades-warlock-guide', 0)),
    'Druid': (('fissure-druid', 2),),
    'Assassin': (('lightning-sentry-assassin', 2), ('wake-of-fire-assassin', 2)),
    'Sorceress': (('lightning-sorceress', 0), ('meteor-sorceress', 1), ('nova-sorceress-guide', 3)),
}
SUFFIX = '-chance-guards-find-absorb-alternative'
BASES = (('Chain Gloves', 10), ('Heavy Bracers', 44), ('Vambraces', 67))


def gloves(base, base_defense, mf=25, ed=20):
    return Item(
        base,
        'unique',
        'Chance Guards',
        (
            (80, 0, mf),
            (79, 0, 200),
            (19, 0, 25),
            (31, 0, base_defense * (100 + ed) // 100 + 15),
            (89, 0, 2),
            (16, 0, ed),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        gold = tuple(g + SUFFIX + '-stats' for g, _ in uses if g == 'gold-find-barbarian')
        context = {'player_class': player_class}
        examples = []
        for base, defense in BASES:
            for label, mf, ed in (
                ('minimum', 25, 20),
                ('perfect', 40, 30),
                ('mf-only-perfect', 40, 20),
                ('defense-only-perfect', 25, 30),
            ):
                examples.append((base + '/' + label, gloves(base, defense, mf, ed), context, 'true'))
        item = gloves('Chain Gloves', 10)
        examples.extend(
            (
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Necromancer'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('impossible-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                annotations = {'80:0': IsPartialDict(configuration_ids=Contains(*configs))}
                if gold:
                    annotations['79:0'] = IsPartialDict(configuration_ids=Contains(*gold))
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=25 if stat == 80 else 20, max=40 if stat == 80 else 30),
                                roll_quality='perfect' if value == (40 if stat == 80 else 30) else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in (80, 16)
                        )
                    )
                )
            yield Case(
                id=f'chance-guards-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations={
                    **dict.fromkeys(('19:0', '31:0', '89:0', '16:0'), configs),
                    '79:0': tuple(c for c in configs if c not in gold),
                },
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Chance Guards', 'Trade tier:') if truth == 'true' else ('Chain Gloves',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/104',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Gloves/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
