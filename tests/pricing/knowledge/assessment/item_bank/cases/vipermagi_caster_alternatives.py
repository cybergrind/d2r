"""Vipermagi standalone alternatives: resistance rolls, upgrades and legal sockets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = (
    ('Warlock', 'caster-core-gear', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        'caster-core-gear',
        (
            ('frozen-orb-sorceress', 29),
            ('frozen-orb-meteor-sorceress', 29),
            ('fire-wall-sorceress-guide', 30),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Necromancer', 'summoner-caster-gear', (('summoner-necromancer-guide', 33),)),
)
MINIMUM = ((127, 0, 1), (105, 0, 30), (16, 0, 120), (35, 0, 9), (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20))
MAXIMUM = ((127, 0, 1), (105, 0, 30), (16, 0, 120), (35, 0, 13), (39, 0, 35), (41, 0, 35), (43, 0, 35), (45, 0, 35))


def cases():
    item = Item('Serpentskin Armor', 'unique', 'Skin of the Vipermagi', MINIMUM)
    # An arbitrary jewel does not turn this standalone alternative into a specific
    # socket recipe, nor give these caster builds an attack-speed benefit.
    jewel = SocketItem('Jewel', ((93, 0, 15),), complete=True)
    for player_class, suffix, sources in USES:
        roles = tuple(f'{guide}-skin-of-the-vipermagi-{suffix}' for guide, _ in sources)
        context = {'player_class': player_class}
        examples = (
            ('minimum-rolls', item, context, 'positive'),
            ('maximum-rolls', replace(item, raw_stats=MAXIMUM), context, 'positive'),
            ('upgraded', replace(item, base='Wyrmhide'), context, 'positive'),
            ('open-socket', replace(item, sockets=1), context, 'positive'),
            (
                'filled-socket',
                replace(
                    item, sockets=1, socket_contents='filled', socket_items=(jewel,), raw_stats=(*MINIMUM, (93, 0, 15))
                ),
                context,
                'positive',
            ),
            ('unread-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'positive'),
            ('ethereal', replace(item, ethereal=True), context, 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'negative'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'negative'),
            ('unread-class', item, {}, 'unknown'),
            ('too-many-sockets', replace(item, sockets=2), context, 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown'),
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
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0', '35:0', '16:0')
                        }
                    )
                )
            yield Case(
                id=f'vipermagi-caster/{player_class.lower()}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if scenario == 'positive' else configs,
                absent_stat_configurations={'93:0': configs},
                report_contains=('Skin of the Vipermagi',)
                if not candidate.identified
                else ('Skin of the Vipermagi', 'Trade tier:'),
                evidence=(
                    *(
                        f'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                        for guide, section in sources
                    ),
                    'third-parties/d2data/json/uniqueitems.json:/210',
                ),
            )


CASES = tuple(cases())
