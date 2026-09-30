"""Explicit combat alternatives and legal upgrade paths from cited guide slots."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    (
        "Nosferatu's Coil",
        'nosferatu-s-coil',
        374,
        ('Vampirefang Belt',),
        ((93, 0, 10), (60, 0, 6), (150, 0, 10), (0, 0, 15), (138, 0, 2)),
        'Belts',
        (
            ('double-throw-barbarian-guide', 'Barbarian', 2),
            ('dream-paladin', 'Paladin', 3),
            ('lightning-fury-amazon-guide', 'Amazon', 5),
            ('strafe-amazon', 'Amazon', 2),
        ),
    ),
    (
        'Goblin Toe',
        'goblin-toe',
        110,
        ('Light Plated Boots', 'Battle Boots', 'Mirrored Boots'),
        ((136, 0, 25), (34, 0, 1), (35, 0, 1), (31, 0, 15), (16, 0, 55)),
        'Boots',
        (
            ('double-throw-barbarian-guide', 'Barbarian', 2),
            ('dream-paladin', 'Paladin', 2),
            ('smite-paladin', 'Paladin', 0),
        ),
    ),
    (
        'Gore Rider',
        'gore-rider',
        241,
        ('War Boots', 'Myrmidon Greaves'),
        ((136, 0, 15), (135, 0, 10), (141, 0, 15), (96, 0, 30), (16, 0, 180)),
        'Boots',
        (
            ('double-throw-barbarian-guide', 'Barbarian', 1),
            ('dream-paladin', 'Paladin', 1),
            ('smite-paladin', 'Paladin', 1),
            ('strafe-amazon', 'Amazon', 2),
        ),
    ),
)


def cases():
    for name, slug, table, bases, stats, slot, uses in GROUPS:
        item = Item(bases[0], 'unique', name, raw_stats=stats)
        for guide, player_class, index in uses:
            role = f'{guide}-{slug}-boots-belts-alternative'
            context = {'player_class': player_class}
            examples = [
                (f'base-{i}', replace(item, base=base), context, 'true', 'positive') for i, base in enumerate(bases)
            ]
            examples.extend(
                (
                    ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                    ('ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
                    ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
                    ('wrong-class', item, {'player_class': 'Necromancer'}, 'false', 'negative'),
                    ('unknown-class', item, {}, 'unknown', 'unknown'),
                    ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                )
            )
            for label, candidate, loadout, truth, scenario in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if scenario == 'positive':
                    keys = ('93:0', '60:0') if slug == 'nosferatu-s-coil' else ('136:0',)
                    if slug == 'gore-rider':
                        keys += ('135:0',)
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'combat-boot-belt-alternative/{guide}/{slug}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario=scenario,
                    covers=(role,),
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations={'141:0': (role + '-stats',)}
                    if guide == 'smite-paladin' and slug == 'gore-rider'
                    else {},
                    report_contains=(name,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{guide}/slots/{slot}/{index}',
                        f'third-parties/d2data/json/uniqueitems.json:/{table}',
                    ),
                )


CASES = tuple(cases())
