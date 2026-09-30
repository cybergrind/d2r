"""Standalone set accessory uses do not imply set completion bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    (
        "Natalya's Soul",
        'natalya-s-soul',
        ('Mesh Boots', 'Boneweave Boots'),
        ((96, 0, 40), (43, 0, 20), (41, 0, 20), (31, 0, 100)),
        ('96:0', '43:0', '41:0'),
        '36:0',
        'Boots',
        (
            ('fissure-druid', 'Druid', 4),
            ('lightning-fury-amazon-guide', 'Amazon', 5),
            ('lightning-sentry-assassin', 'Assassin', 3),
            ('lightning-strike-amazon', 'Amazon', 4),
            ('wake-of-fire-assassin', 'Assassin', 3),
        ),
    ),
    (
        "Trang-Oul's Girth",
        'trang-oul-s-girth',
        ('Troll Belt',),
        ((153, 0, 1), (7, 0, 66 * 256), (9, 0, 40 * 256), (31, 0, 85)),
        ('153:0', '7:0', '9:0'),
        '43:0',
        'Belts',
        (('gold-find-barbarian', 'Barbarian', 2), ('smite-paladin', 'Paladin', 4)),
    ),
)


def cases():
    for name, slug, bases, stats, keys, excluded, slot, uses in GROUPS:
        item = Item(bases[0], 'set', name, raw_stats=stats)
        for guide, player_class, index in uses:
            role = f'{guide}-{slug}-boots-belts-alternative'
            context = {'player_class': player_class, 'player_items': []}
            examples = [
                (f'base-{i}', replace(item, base=base), context, 'true', 'positive') for i, base in enumerate(bases)
            ]
            examples.extend(
                (
                    ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
                    ('impossible-ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
                    ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
                    ('wrong-class', item, {'player_class': 'Necromancer'}, 'false', 'negative'),
                    ('unread-class', item, {}, 'unknown', 'unknown'),
                    ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
                    ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                    (
                        'captured-conditional-stat',
                        replace(item, raw_stats=(*stats, (int(excluded.split(':')[0]), 0, 40))),
                        context,
                        'true',
                        'positive',
                    ),
                )
            )
            for label, candidate, loadout, truth, scenario in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'standalone-set-accessory/{guide}/{slug}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario=scenario,
                    covers=(role,),
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations={excluded: (role + '-stats',)},
                    report_contains=(name,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{guide}/slots/{slot}/{index}',
                        f'third-parties/d2data/json/setitems.json:/{name}',
                    ),
                )


CASES = tuple(cases())
