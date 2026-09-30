"""Oculus caster utility survives legal upgrades; random Teleport is not passive utility."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SLOTS = (('blizzard-sorceress', 4), ('lightning-sorceress', 2), ('meteor-sorceress', 3), ('nova-sorceress-guide', 3))
TABLES = (
    ('fire-wall-sorceress-guide', 30),
    ('frozen-orb-meteor-sorceress', 29),
    ('frozen-orb-sorceress', 29),
    ('hydra-sorceress', 29),
)
ROLES = (
    *(g + '-the-oculus-jewelry-casting-alternative' for g, _ in SLOTS),
    *(g + '-the-oculus-caster-weapon-gear' for g, _ in TABLES),
)


def cases():
    for base in ('Swirling Crystal', 'Dimensional Shard'):
        item = Item(
            base,
            'unique',
            'The Oculus',
            raw_stats=(
                (83, 1, 3),
                (105, 0, 30),
                (80, 0, 50),
                (39, 0, 20),
                (41, 0, 20),
                (43, 0, 20),
                (45, 0, 20),
                (3, 0, 20),
                (1, 0, 20),
                (138, 0, 5),
                (16, 0, 20),
                (201, 54 * 64 + 1, 25),
            ),
        )
        context = {'player_class': 'Sorceress'}
        for label, candidate, loadout, truth in (
            ('native-stats', item, context, 'true'),
            ('open-socket', replace(item, sockets=1), context, 'true'),
            ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
            ('ethereal-casting', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal-casting', replace(item, ethereal=None), context, 'true'),
            ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in ROLES)))
                            for key in ('83:1', '105:0', '80:0', '39:0', '41:0', '43:0', '45:0', '3:0', '1:0', '138:0')
                        }
                    )
                )
            yield Case(
                id=f'oculus-alternatives/{base}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=ROLES,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations={'201:3457': tuple(role + '-stats' for role in ROLES)},
                report_contains=(
                    'The Oculus',
                    '30% Faster Cast Rate',
                    '25% Chance to cast level 1 Teleport when struck',
                    'Trade tier:',
                )
                if truth == 'true'
                else (base,),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/284',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Weapon/{i}' for g, i in SLOTS),
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{g}.html/sections/{n}'
                        for g, n in TABLES
                    ),
                ),
            )


CASES = tuple(cases())
