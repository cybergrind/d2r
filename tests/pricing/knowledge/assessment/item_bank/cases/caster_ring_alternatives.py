"""Caster ring skills, level-scaled life and fire defense; no spell leech credit."""

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
        "Bul-Kathos' Wedding Band",
        'bul-kathos-wedding-band',
        268,
        ((127, 0, 1), (216, 0, 4 * 256), (60, 0, 3)),
        ('127:0', '216:0'),
        (60, 5),
    ),
    (
        'Dwarf Star',
        'dwarf-star',
        274,
        ((142, 0, 15), (35, 0, 12), (7, 0, 40 * 256), (79, 0, 100)),
        ('142:0', '35:0', '7:0'),
        (35, 15),
    ),
)


def cases():
    for name, slug, table, stats, keys, high_roll in ITEMS:
        item = Item('Ring', 'unique', name, raw_stats=stats)
        for player_class, suffix, sources in USES:
            if slug == 'dwarf-star' and player_class != 'Sorceress':
                continue
            roles = tuple(f'{guide}-{slug}-{suffix}' for guide, _ in sources)
            context = {'player_class': player_class}
            examples = (
                ('minimum-roll', item, context, 'true', 'positive'),
                (
                    'maximum-roll',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, high_roll[1] if stat == high_roll[0] else value)
                            for stat, layer, value in stats
                        ),
                    ),
                    context,
                    'true',
                    'positive',
                ),
                ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                ('impossible-ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
                ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
                ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
                ('unread-class', item, {}, 'unknown', 'unknown'),
                ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
                ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
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
                            {
                                key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))
                                for key in keys
                            }
                        )
                    )
                yield Case(
                    id=f'caster-ring-alternative/{slug}/{player_class}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario=scenario,
                    covers=roles,
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations={'60:0': tuple(role + '-stats' for role in roles)},
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
