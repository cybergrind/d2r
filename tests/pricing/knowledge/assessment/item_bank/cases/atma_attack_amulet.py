"""Atma's Scarab: physical projectile proc utility, not permanent curse uptime."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Native row273: poison rate102 for100frames; 5% level2 Amplify Damage.
ATMA = Item(
    'Amulet',
    'unique',
    "Atma's Scarab",
    (
        (57, 0, 102),
        (58, 0, 102),
        (59, 0, 100),
        (326, 0, 1),
        (45, 0, 75),
        (89, 0, 3),
        (78, 0, 5),
        (198, 66 * 64 + 2, 5),
        (119, 0, 20),
    ),
    named_table_id=273,
    complete=True,
)


def cases():
    for build, klass, slot_index in (
        ('strafe-amazon', 'Amazon', 0),
        ('double-throw-barbarian-guide', 'Barbarian', 2),
    ):
        role = f'{build}-atma-s-scarab-attack-utility-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        for label, item, loadout, truth in (
            ('physical-projectiles', ATMA, context, 'true'),
            (
                'unknown-poison-count',
                replace(ATMA, complete=False, raw_stats=tuple(row for row in ATMA.raw_stats if row[0] != 326)),
                context,
                'true',
            ),
            ('wrong-wearer', ATMA, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-wearer', ATMA, {}, 'unknown'),
            ('impossible-ethereal', replace(ATMA, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(ATMA, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(ATMA, sockets=1), context, 'false'),
            ('unknown-sockets', replace(ATMA, sockets=None), context, 'unknown'),
        ):
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config), desirability=grade)
                            for key, grade in (
                                ('198:4226', 'desirable'),
                                ('119:0', 'desirable'),
                                ('45:0', 'supporting'),
                            )
                        }
                    )
                )
            if label == 'physical-projectiles':
                expected['contract'] = IsPartialDict(
                    policy='named',
                    family='jewelry',
                    name="Atma's Scarab",
                    intrinsic_properties=IsPartialDict({'589': 40, '543': 5, '424': 20}),
                )
            if label == 'unknown-poison-count':
                expected['contract'] = None
                expected['price_gaps'] = Contains('Named fixed poison components are missing, changed or unverified.')
            yield Case(
                id=f'atma-attack/{build}/{label}',
                item=item,
                context=loadout,
                covers=(role,),
                scenario='unknown'
                if label == 'unknown-poison-count'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={
                    'assessment': IsPartialDict(**expected),
                    **({'price_estimate': IsPartialDict(estimate_ist=None)} if label == 'unknown-poison-count' else {}),
                },
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(('57:0', '58:0', '78:0', '89:0'), (config,)),
                report_contains=(
                    "Atma's Scarab",
                    'Trade tier:',
                    'Amplify Damage',
                    '20% Bonus to Attack Rating',
                    'Poison duration total: 4 seconds'
                    if label == 'unknown-poison-count'
                    else '40 Poison Damage over 4 Seconds',
                    'Poison Resist +75%',
                )
                if active
                else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/Amulets/{slot_index}',
                    'third-parties/d2data/json/uniqueitems.json:/273',
                ),
            )


CASES = tuple(cases())
