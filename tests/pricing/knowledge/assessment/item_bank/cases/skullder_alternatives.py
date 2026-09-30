"""Magic-find armor alternatives retain wearer-level and self-repair distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    (
        'Warlock',
        (
            ('abyss-warlock-build-guide', 'Body Armors', 5),
            ('echoing-strike-warlock-guide', 'Body Armors', 5),
            ('fire-warlock-guide', 'Body Armors', 7),
            ('mirrored-blades-warlock-guide', 'Body Armors', 3),
        ),
    ),
    ('Barbarian', (('berserk-barbarian', 'Body Armor', 1), ('double-throw-barbarian-guide', 'Body Armor', 5))),
    (
        'Paladin',
        (
            ('blessed-hammer-paladin', 'Body Armors', 2),
            ('dream-paladin', 'Body Armor', 4),
            ('fist-of-the-heavens-paladin', 'Body Armors', 2),
        ),
    ),
    (
        'Sorceress',
        (
            ('blizzard-sorceress', 'Body Armor', 4),
            ('enchant-sorceress', 'Body Armor', 2),
            ('lightning-sorceress', 'Body Armors', 4),
            ('meteor-sorceress', 'Body Armor', 4),
        ),
    ),
    ('Druid', (('fissure-druid', 'Body Armor', 1),)),
    ('Amazon', (('lightning-fury-amazon-guide', 'Body Armors', 4), ('lightning-strike-amazon', 'Body Armor', 3))),
    ('Assassin', (('lightning-sentry-assassin', 'Body Armor', 4), ('wake-of-fire-assassin', 'Body Armor', 5))),
    ('Necromancer', (('poison-nova-necromancer', 'Body Armor', 3),)),
)
CORE = ((127, 0, 1), (240, 0, 10), (16, 0, 160), (35, 0, 10))


def cases():
    item = Item('Russet Armor', 'unique', "Skullder's Ire", (*CORE, (252, 0, 20)), complete=True, viewer_level=80)
    for player_class, sources in USES:
        roles = tuple(
            f'{guide}-skullder-{slot.lower().replace(" ", "-")}-utility-alternative' for guide, slot, _ in sources
        )
        evidence = tuple(
            f'pricing/data/wp-a-builds.json:/{guide}/slots/{slot}/{index}' for guide, slot, index in sources
        )
        if player_class == 'Necromancer':
            roles += ('summoner-necromancer-guide-skullder-s-ire-summoner-caster-gear',)
            evidence += (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                'pricing~1raw~1mr~1guides__summoner-necromancer-guide.html/sections/33',
            )
        context = {'player_class': player_class}
        examples = (
            ('level-80', item, context, 'positive'),
            ('level-48', replace(item, viewer_level=48), context, 'positive'),
            ('upgraded', replace(item, base='Balrog Skin'), context, 'positive'),
            ('open-socket', replace(item, sockets=1), context, 'positive'),
            ('unread-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'positive'),
            ('invalid-sockets', replace(item, sockets=2), context, 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown'),
            ('ethereal-repair', replace(item, ethereal=True), context, 'positive'),
            ('ethereal-no-repair', replace(item, ethereal=True, raw_stats=CORE), context, 'negative'),
            (
                'ethereal-unread-repair',
                replace(item, ethereal=True, raw_stats=CORE, complete=False),
                context,
                'unknown',
            ),
            ('nonethereal-unread-repair', replace(item, raw_stats=CORE, complete=False), context, 'positive'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'negative'),
            ('wrong-class', item, {'player_class': 'Druid' if player_class != 'Druid' else 'Warlock'}, 'negative'),
            ('unread-class', item, {}, 'unknown'),
        )
        for label, candidate, loadout, scenario in examples:
            configs = tuple(role + '-stats' for role in roles)
            expected = {
                'roles': Contains(
                    *(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(
                                truth={
                                    'positive': 'true',
                                    'negative': 'false',
                                    'unknown': 'unknown',
                                }[scenario]
                            ),
                        )
                        for role in roles
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in ('127:0', '240:0', '35:0')}
                    )
                )
            yield Case(
                id=f'skullder-alternative/{player_class.lower()}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if scenario == 'positive' else configs,
                report_contains=("Skullder's Ire",)
                + (
                    (('100%' if label == 'level-80' else '60%') + ' Better Chance of Getting Magic Items',)
                    if label in ('level-80', 'level-48')
                    else ()
                ),
                evidence=(*evidence, 'third-parties/d2data/json/uniqueitems.json:/217'),
            )


CASES = tuple(cases())
