"""Independent Annihilus rolls across reviewed caster gear tables."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Warlock': (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29)),
    'Sorceress': (
        ('fire-wall-sorceress-guide', 30),
        ('frozen-orb-meteor-sorceress', 29),
        ('frozen-orb-sorceress', 29),
        ('hydra-sorceress', 29),
    ),
}
ATTRIBUTES = (0, 1, 2, 3)
RESISTS = (39, 41, 43, 45)


def charm(attributes=10, resistance=10, experience=5):
    return Item(
        'Small Charm',
        'unique',
        'Annihilus',
        (
            (127, 0, 1),
            *((stat, 0, attributes) for stat in ATTRIBUTES),
            *((stat, 0, resistance) for stat in RESISTS),
            (85, 0, experience),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + '-annihilus-gear-inventory-charm' for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        item = charm()
        context = {'player_class': player_class}
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', charm(20, 20, 10), context, 'true'),
            ('attributes-only-perfect', charm(20, 10, 5), context, 'true'),
            ('resistance-only-perfect', charm(10, 20, 5), context, 'true'),
            ('experience-only-perfect', charm(10, 10, 10), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{stat}:0': IsPartialDict(configuration_ids=Contains(*configs))
                            for stat in (127, *ATTRIBUTES, *RESISTS, 85)
                        }
                    )
                )
                result['assessment'] = IsPartialDict(**expected)
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=5 if stat == 85 else 10, max=10 if stat == 85 else 20),
                                roll_quality='perfect' if value == (10 if stat == 85 else 20) else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat != 127
                        )
                    )
                )
            yield Case(
                id=f'annihilus-tables/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Annihilus', 'Trade tier:') if truth == 'true' else ('Small Charm',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/381',
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{g}.html/sections/{i}'
                        for g, i in uses
                    ),
                ),
            )


CASES = tuple(cases())
