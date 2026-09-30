"""Abyss table boots: native rolls, upgrades, self-repair and caster recipes."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'waterwalk',
        'abyss-warlock-build-guide-waterwalk-boots-alternative',
        Item('Sharkskin Boots', 'unique', 'Waterwalk', ((96, 0, 20), (7, 0, 45 * 256), (2, 0, 15), (40, 0, 5))),
        ('Sharkskin Boots', 'Scarabshell Boots'),
        ('96:0', '7:0', '2:0', '40:0'),
        ('39:0',),
    ),
    (
        'trek',
        'abyss-warlock-build-guide-trek-boots-alternative',
        Item(
            'Scarabshell Boots',
            'unique',
            'Sandstorm Trek',
            ((96, 0, 20), (99, 0, 20), (0, 0, 10), (3, 0, 10), (45, 0, 40), (252, 0, 5)),
        ),
        ('Scarabshell Boots',),
        ('96:0', '99:0', '0:0', '3:0', '45:0'),
        (),
    ),
    (
        'aldur',
        'abyss-warlock-build-guide-aldur-boots-alternative',
        Item('Battle Boots', 'set', "Aldur's Advance", ((96, 0, 40), (7, 0, 50 * 256), (39, 0, 40))),
        ('Battle Boots', 'Mirrored Boots'),
        ('96:0', '7:0', '39:0'),
        ('2:0',),
    ),
    (
        'silkweave',
        'abyss-warlock-build-guide-silkweave-caster-progression-alternative',
        Item('Mesh Boots', 'unique', 'Silkweave', ((96, 0, 30), (77, 0, 10), (138, 0, 5), (32, 0, 200))),
        ('Mesh Boots', 'Boneweave Boots'),
        ('96:0', '77:0', '138:0', '32:0'),
        ('62:0',),
    ),
    (
        'wraithstep',
        'abyss-warlock-table-boots-wraithstep',
        Item(
            'Mirrored Boots',
            'unique',
            'Wraithstep',
            ((188, 58, 1), (96, 0, 30), (99, 0, 20), (31, 0, 100), (2, 0, 10), (1, 0, 10)),
        ),
        ('Mirrored Boots',),
        ('188:58', '96:0', '99:0', '31:0', '2:0', '1:0'),
        ('188:56', '188:57'),
    ),
    (
        'legacy',
        'abyss-warlock-table-boots-legacy',
        Item(
            'Mirrored Boots',
            'set',
            "Horazon's Legacy",
            ((96, 0, 30), (0, 0, 10), (2, 0, 10), (37, 0, 20), (153, 0, 1), (91, 0, -30)),
        ),
        ('Mirrored Boots',),
        ('96:0', '0:0', '2:0', '37:0', '153:0', '91:0'),
        ('35:0',),
    ),
    (
        'traveler',
        'abyss-warlock-table-boots-traveler',
        Item(
            'Battle Boots',
            'unique',
            'War Traveler',
            ((80, 0, 30), (96, 0, 25), (0, 0, 10), (3, 0, 10), (16, 0, 150), (21, 0, 15), (22, 0, 25)),
        ),
        ('Battle Boots', 'Mirrored Boots'),
        ('80:0', '96:0', '0:0', '3:0', '16:0'),
        ('21:0', '22:0'),
    ),
    (
        'crafted',
        'abyss-warlock-table-boots-crafted',
        Item('Boots', 'crafted', 'Imp Blazer', ((27, 0, 4), (9, 0, 10 * 256), (77, 0, 2))),
        ('Boots', 'Demonhide Boots', 'Wyrmhide Boots'),
        ('27:0', '9:0', '77:0'),
        ('105:0',),
    ),
)


def cases():
    for slug, role, original, bases, keys, incidental in EXAMPLES:
        for base in bases:
            item = replace(original, base=base)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
                ('unknown-class', item, {}, 'unknown', ()),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
                ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
                (
                    'ethereal',
                    replace(item, ethereal=True),
                    {'player_class': 'Warlock'},
                    'true' if slug == 'trek' else 'false',
                    keys,
                ),
            ]
            if slug == 'trek':
                rows += [
                    (
                        'no-repair',
                        replace(item, ethereal=True, raw_stats=item.raw_stats[:-1], complete=True),
                        {'player_class': 'Warlock'},
                        'false',
                        (),
                    ),
                    (
                        'unknown-repair',
                        replace(item, ethereal=True, raw_stats=item.raw_stats[:-1]),
                        {'player_class': 'Warlock'},
                        'unknown',
                        (),
                    ),
                ]
            if slug == 'wraithstep':
                rows += [
                    (
                        'wrong-tab',
                        replace(item, raw_stats=((188, 56, 1), *item.raw_stats[1:]), complete=True),
                        {'player_class': 'Warlock'},
                        'false',
                        (),
                    ),
                    (
                        'unknown-tab',
                        replace(item, raw_stats=item.raw_stats[1:]),
                        {'player_class': 'Warlock'},
                        'unknown',
                        (),
                    ),
                ]
            if slug == 'crafted':
                affixes = ((96, 0, 30), (99, 0, 10), (39, 0, 40), (80, 0, 25))
                rows += [
                    (
                        'affixes',
                        replace(item, raw_stats=item.raw_stats + affixes),
                        {'player_class': 'Warlock'},
                        'true',
                        (*keys, '96:0', '99:0', '39:0', '80:0'),
                    ),
                    (
                        'missing-recipe-stat',
                        replace(item, raw_stats=item.raw_stats[:-1], complete=True),
                        {'player_class': 'Warlock'},
                        'false',
                        (),
                    ),
                    (
                        'unknown-recipe-stat',
                        replace(item, raw_stats=item.raw_stats[:-1]),
                        {'player_class': 'Warlock'},
                        'unknown',
                        (),
                    ),
                ]
            for label, candidate, context, truth, expected_keys in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in expected_keys}
                        )
                    )
                yield Case(
                    id=f'abyss/boots/{slug}/{base}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(incidental, (role + '-stats',)),
                    report_contains=(base if slug == 'crafted' else original.name,),
                    evidence=('pricing/data/appraisal-guide-sections.json', 'third-parties/d2data/json/cubemain.json'),
                )


CASES = tuple(cases())
