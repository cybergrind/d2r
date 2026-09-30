"""Waterwalk alternatives: life, movement and maximum fire resistance."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Warlock', (('echoing-strike-warlock-guide', 0), ('fire-warlock-guide', 1), ('mirrored-blades-warlock-guide', 0))),
    ('Assassin', (('fire-blast-assassin', 1), ('lightning-sentry-assassin', 2), ('wake-of-fire-assassin', 2))),
    ('Paladin', (('fist-of-the-heavens-paladin', 0), ('smite-paladin', 3))),
    ('Sorceress', (('meteor-sorceress', 2), ('nova-sorceress-guide', 3))),
    ('Necromancer', (('poison-nova-necromancer', 2),)),
)


SECTION_USES = {
    'Warlock': (
        ('blood-boil-warlock-guide', 29, 'caster-accessory-gear'),
        ('summoner-warlock-guide', 29, 'caster-accessory-gear'),
    ),
    'Sorceress': (
        ('frozen-orb-sorceress', 29, 'caster-accessory-gear'),
        ('frozen-orb-meteor-sorceress', 29, 'caster-accessory-gear'),
        ('fire-wall-sorceress-guide', 30, 'caster-accessory-gear'),
        ('hydra-sorceress', 29, 'caster-accessory-gear'),
    ),
}


def cases():
    stats = ((96, 0, 20), (7, 0, 45 * 256), (2, 0, 15), (40, 0, 5), (16, 0, 195))
    item = Item('Sharkskin Boots', 'unique', 'Waterwalk', raw_stats=stats)
    for player_class, sources in USES:
        roles = tuple(guide + '-waterwalk-boots-alternative' for guide, _ in sources)
        sections = SECTION_USES.get(player_class, ())
        roles += tuple(f'{guide}-waterwalk-{suffix}' for guide, _, suffix in sections)
        context = {'player_class': player_class}
        examples = (
            ('minimum-life', item, context, 'true', 'positive'),
            (
                'maximum-life',
                replace(
                    item,
                    raw_stats=tuple((stat, layer, 65 * 256 if stat == 7 else value) for stat, layer, value in stats),
                ),
                context,
                'true',
                'positive',
            ),
            ('upgraded', replace(item, base='Scarabshell Boots'), context, 'true', 'positive'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
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
                            for key in ('96:0', '7:0', '40:0')
                        }
                    )
                )
            yield Case(
                id=f'waterwalk-alternative/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                report_contains=('Waterwalk',),
                evidence=(
                    *(f'pricing/data/wp-a-builds.json:/{guide}/slots/Boots/{index}' for guide, index in sources),
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section, _ in sections
                    ),
                    'third-parties/d2data/json/uniqueitems.json:/238',
                ),
            )


CASES = tuple(cases())
