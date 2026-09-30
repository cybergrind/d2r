"""Ethereal Sandstorm Trek utility requires observed self-repair evidence."""

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


def cases():
    core = ((96, 0, 20), (99, 0, 20), (0, 0, 10), (3, 0, 10), (45, 0, 40), (16, 0, 140))
    item = Item('Scarabshell Boots', 'unique', 'Sandstorm Trek', raw_stats=(*core, (252, 0, 5)), complete=True)
    for player_class, suffix, sources in USES:
        roles = tuple(f'{guide}-sandstorm-trek-{suffix}' for guide, _ in sources)
        context = {'player_class': player_class}
        examples = (
            ('minimum-rolls', item, context, 'true', 'positive'),
            ('ethereal-repairs', replace(item, ethereal=True), context, 'true', 'positive'),
            ('ethereal-no-repair', replace(item, ethereal=True, raw_stats=core), context, 'false', 'negative'),
            (
                'ethereal-unread-repair',
                replace(item, ethereal=True, raw_stats=core, complete=False),
                context,
                'unknown',
                'unknown',
            ),
            ('nonethereal-unread-repair', replace(item, raw_stats=core, complete=False), context, 'true', 'positive'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
            ('unread-class', item, {}, 'unknown', 'unknown'),
            ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
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
                            for key in ('96:0', '99:0', '0:0', '3:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'sandstorm-caster-alternative/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                report_contains=('Sandstorm Trek',),
                evidence=(
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section in sources
                    ),
                    'third-parties/d2data/json/uniqueitems.json:/369',
                ),
            )


CASES = tuple(cases())
