"""Exact guide alternatives; attack damage is not elemental spell/aura scaling."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'Azurewrath',
        'Phase Blade',
        301,
        'dream-paladin',
        'Paladin',
        'Weapon',
        2,
        'attack-utility-alternative',
        (
            (17, 0, 230),
            (18, 0, 230),
            (151, 119, 10),
            (127, 0, 1),
            (93, 0, 30),
            (52, 0, 250),
            (53, 0, 500),
            (54, 0, 250),
            (55, 0, 500),
            (56, 0, 250),
            (0, 0, 5),
            (1, 0, 5),
            (2, 0, 5),
            (3, 0, 5),
            (89, 0, 3),
        ),
        {17: 270, 18: 270, 151: 13, 0: 10, 1: 10, 2: 10, 3: 10},
        ('127:0', '93:0', '151:119'),
        ('17:0', '18:0', '52:0', '53:0', '54:0', '55:0'),
        ('(230-270%)', '(10-13)', 'Sanctuary', '250-500 Magic Damage', '250-500 Cold Damage'),
    ),
    (
        'Lightsabre',
        'Phase Blade',
        259,
        'dream-paladin',
        'Paladin',
        'Weapon',
        3,
        'attack-utility-alternative',
        (
            (17, 0, 150),
            (18, 0, 150),
            (62, 0, 5),
            (144, 0, 25),
            (93, 0, 20),
            (115, 0, 1),
            (52, 0, 60),
            (53, 0, 120),
            (50, 0, 1),
            (51, 0, 200),
            (89, 0, 7),
        ),
        {17: 200, 18: 200, 62: 7},
        ('93:0', '144:0'),
        ('17:0', '18:0', '62:0', '115:0'),
        ('(150-200%)', '(5-7%)', 'Lightning Absorb +25%', '60-120 Magic Damage', '1-200 Lightning Damage'),
    ),
    (
        'Snowclash',
        'Battle Belt',
        245,
        'blizzard-sorceress',
        'Sorceress',
        'Belts',
        2,
        'caster-shield-alternative',
        (
            (16, 0, 130),
            (107, 59, 2),
            (107, 55, 3),
            (107, 60, 2),
            (149, 0, 15),
            (44, 0, 15),
            (54, 0, 13),
            (55, 0, 21),
            (56, 0, 75),
        ),
        {16: 170},
        ('107:59', '149:0', '44:0'),
        ('107:55', '107:60'),
        ('(130-170%)', 'Blizzard', 'Glacial Spike', 'Chilling Armor', '13-21 Cold Damage'),
    ),
)


def cases():
    for name, base, table, build, klass, slot, index, suffix, stats, high, desirable, supporting, report in SPECS:
        role = f'{build}-{name.lower()}-{suffix}'
        config = role + '-stats'
        # Partial native arrays: level-scaled chance-to-cast levels and physical
        # base damage are not invented from the definition's zero placeholders.
        item = Item(base, 'unique', name, stats, named_table_id=table)
        context = {'player_class': klass}
        examples = [
            ('minimum-roll', item, context, 'true'),
            (
                'maximum-roll',
                replace(item, raw_stats=tuple((sid, layer, high.get(sid, raw)) for sid, layer, raw in stats)),
                context,
                'true',
            ),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unknown-sockets', replace(item, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ]
        if name == 'Snowclash':
            examples.extend(
                (
                    ('upgraded', replace(item, base='Troll Belt'), context, 'true'),
                    ('impossible-socket', replace(item, sockets=1), context, 'false'),
                )
            )
        else:
            examples.extend(
                (
                    ('open-socket', replace(item, sockets=1), context, 'true'),
                    ('too-many-sockets', replace(item, sockets=2), context, 'false'),
                )
            )
        for label, candidate, loadout, truth in examples:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config), desirability=grade)
                            for keys, grade in ((desirable, 'desirable'), (supporting, 'supporting'))
                            for key in keys
                        }
                    )
                )
            yield Case(
                id=f'elemental-named/{name}/{label}',
                item=candidate,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(('54:0', '55:0') if name == 'Snowclash' else (), (config,)),
                report_contains=(name, 'Trade tier:', *report) if active else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/slots/{slot}/{index}',
                    f'third-parties/d2data/json/uniqueitems.json:/{table}',
                ),
            )


CASES = tuple(cases())
