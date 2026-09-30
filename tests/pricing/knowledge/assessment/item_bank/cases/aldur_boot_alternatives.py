"""Aldur boots: shared native properties, explicitly cited per-build alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Warlock', (('echoing-strike-warlock-guide', 3), ('fire-warlock-guide', 4), ('mirrored-blades-warlock-guide', 3))),
    ('Sorceress', (('enchant-sorceress', 1), ('lightning-sorceress', 1), ('meteor-sorceress', 4))),
    ('Assassin', (('fire-blast-assassin', 2), ('lightning-sentry-assassin', 0), ('wake-of-fire-assassin', 0))),
    ('Druid', (('fissure-druid', 1),)),
    ('Paladin', (('fist-of-the-heavens-paladin', 3), ('smite-paladin', 4))),
    ('Amazon', (('lightning-fury-amazon-guide', 1), ('lightning-strike-amazon', 3), ('strafe-amazon', 3))),
    ('Necromancer', (('poison-nova-necromancer', 1),)),
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
    'Necromancer': (('summoner-necromancer-guide', 33, 'summoner-caster-gear'),),
}


def cases():
    stats = ((96, 0, 40), (7, 0, 50 * 256), (39, 0, 45), (152, 0, 1))
    item = Item('Battle Boots', 'set', "Aldur's Advance", raw_stats=stats)
    for player_class, sources in USES:
        roles = tuple(guide + '-aldur-boots-alternative' for guide, _ in sources)
        sections = SECTION_USES.get(player_class, ())
        roles += tuple(f'{guide}-aldur-s-advance-{suffix}' for guide, _, suffix in sections)
        context = {'player_class': player_class, 'player_items': []}
        examples = (
            ('native', item, context, 'true', 'positive'),
            ('upgraded', replace(item, base='Mirrored Boots'), context, 'true', 'positive'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
            ('unread-class', item, {}, 'unknown', 'unknown'),
            ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
            ('conditional-dexterity', replace(item, raw_stats=(*stats, (2, 0, 15))), context, 'true', 'positive'),
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
                            for key in ('96:0', '7:0', '39:0')
                        }
                    )
                )
            yield Case(
                id=f'aldur-boot-alternative/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations={'2:0': tuple(role + '-stats' for role in roles)},
                report_contains=("Aldur's Advance",),
                evidence=(
                    *(f'pricing/data/wp-a-builds.json:/{guide}/slots/Boots/{index}' for guide, index in sources),
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section, _ in sections
                    ),
                    "third-parties/d2data/json/setitems.json:/Aldur's Advance",
                ),
            )


CASES = tuple(cases())
