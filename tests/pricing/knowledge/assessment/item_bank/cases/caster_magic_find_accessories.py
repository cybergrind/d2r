"""MF caster accessories retain farming utility without weapon-stat credit."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Warlock', 'caster-accessory-gear', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        'caster-accessory-gear',
        (
            ('frozen-orb-sorceress', 29),
            ('frozen-orb-meteor-sorceress', 29),
            ('fire-wall-sorceress-guide', 30),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Necromancer', 'summoner-caster-gear', (('summoner-necromancer-guide', 33),)),
)
ITEMS = (
    (
        'Chance Guards',
        'chance-guards',
        104,
        ('Chain Gloves', 'Heavy Bracers', 'Vambraces'),
        ((80, 0, 25), (79, 0, 200), (19, 0, 25), (31, 0, 15), (16, 0, 20)),
        '19:0',
    ),
    (
        'Goldwrap',
        'goldwrap',
        115,
        ('Heavy Belt', 'Battle Belt', 'Troll Belt'),
        ((80, 0, 30), (79, 0, 50), (93, 0, 10), (31, 0, 25), (16, 0, 40)),
        '93:0',
    ),
)


def cases():
    for name, slug, table, bases, stats, attack_stat in ITEMS:
        item = Item(bases[0], 'unique', name, raw_stats=stats)
        for player_class, suffix, sources in USES:
            roles = tuple(f'{guide}-{slug}-{suffix}' for guide, _ in sources)
            context = {'player_class': player_class}
            examples = [
                (f'base-{i}', replace(item, base=base), context, 'true', 'positive') for i, base in enumerate(bases)
            ]
            examples.extend(
                (
                    ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                    ('ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
                    ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
                    ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
                    ('unread-class', item, {}, 'unknown', 'unknown'),
                    ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
                    ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                )
            )
            for label, candidate, loadout, truth, scenario in examples:
                expected = {
                    'roles': Contains(
                        *[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles]
                    )
                }
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {'80:0': IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))}
                        )
                    )
                yield Case(
                    id=f'caster-mf-accessory/{slug}/{player_class}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario=scenario,
                    covers=roles,
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations={attack_stat: tuple(role + '-stats' for role in roles)},
                    report_contains=(name,),
                    evidence=(
                        *(
                            'pricing/data/appraisal-guide-sections.json:/sources/'
                            f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                            for guide, section in sources
                        ),
                        f'third-parties/d2data/json/uniqueitems.json:/{table}',
                    ),
                )


CASES = tuple(cases())
