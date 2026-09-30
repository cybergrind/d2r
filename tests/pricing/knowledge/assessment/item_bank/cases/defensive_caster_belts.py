"""Defensive belt benefits for spell and summon setups, separate from life leech."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    (
        "Verdungo's Hearty Cord",
        'verdungo-s-hearty-cord',
        376,
        ('Mithril Coil',),
        'Sorceress',
        'caster-accessory-gear',
        ((36, 0, 10), (3, 0, 30), (99, 0, 10), (74, 0, 10), (16, 0, 90)),
        ((36, 0, 15), (3, 0, 40), (99, 0, 10), (74, 0, 13), (16, 0, 140)),
        ('36:0', '3:0', '99:0', '74:0'),
        (
            ('frozen-orb-sorceress', 29),
            ('frozen-orb-meteor-sorceress', 29),
            ('fire-wall-sorceress-guide', 30),
            ('hydra-sorceress', 29),
        ),
    ),
    (
        'String of Ears',
        'string-of-ears',
        242,
        ('Demonhide Sash', 'Spiderweb Sash'),
        'Necromancer',
        'summoner-caster-gear',
        ((36, 0, 10), (35, 0, 10), (60, 0, 6), (16, 0, 150), (31, 0, 15)),
        ((36, 0, 15), (35, 0, 15), (60, 0, 8), (16, 0, 180), (31, 0, 15)),
        ('36:0', '35:0'),
        (('summoner-necromancer-guide', 33),),
    ),
)


def cases():
    for name, slug, table, bases, player_class, suffix, low, high, keys, sources in GROUPS:
        item = Item(bases[0], 'unique', name, raw_stats=low)
        roles = tuple(f'{guide}-{slug}-{suffix}' for guide, _ in sources)
        context = {'player_class': player_class}
        examples = [
            (f'base-{i}', replace(item, base=base), context, 'true', 'positive') for i, base in enumerate(bases)
        ]
        examples.extend(
            (
                ('maximum-rolls', replace(item, raw_stats=high), context, 'true', 'positive'),
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
                'roles': Contains(*[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles])
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
                id=f'defensive-caster-belt/{slug}/{label}',
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
