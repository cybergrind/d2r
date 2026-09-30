"""Native minimums and optional affixes for the remaining Abyss glove/belt table."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'horazon',
        Item(
            'Demonhide Gloves',
            'set',
            "Horazon's Hold",
            (
                (2, 0, 10),
                (7, 0, 30 * 256),
                (136, 0, 10),
                (19, 0, 95),
                (48, 0, 140),
                (49, 0, 270),
            ),
        ),
        ('Demonhide Gloves', 'Bramble Mitts'),
        ('2:0', '7:0'),
        ('136:0', '19:0', '48:0', '49:0', '93:0', '60:0', '62:0'),
    ),
    (
        'gheed',
        Item(
            'Troll Belt',
            'unique',
            "Gheed's Wager",
            (
                (105, 0, 10),
                (99, 0, 10),
                (96, 0, 10),
                (16, 0, 90),
                (358, 0, 3),
                (39, 0, 5),
                (41, 0, 5),
                (43, 0, 5),
                (45, 0, 5),
                (79, 0, 44),
            ),
        ),
        ('Troll Belt',),
        ('105:0', '99:0', '96:0', '16:0', '358:0', '39:0', '41:0', '43:0', '45:0', '79:0'),
        (),
    ),
    (
        'bane',
        Item('Light Belt', 'set', "Bane's Authority", ((105, 0, 10), (7, 0, 20 * 256))),
        ('Light Belt', 'Sharkskin Belt', 'Vampirefang Belt'),
        ('105:0', '7:0'),
        ('1:0',),
    ),
    (
        'crafted-gloves',
        Item('Bramble Mitts', 'crafted', 'Caster Crafted', ((27, 0, 4), (9, 0, 10 * 256), (138, 0, 1))),
        ('Leather Gloves', 'Demonhide Gloves', 'Bramble Mitts'),
        ('27:0', '9:0', '138:0'),
        ('105:0',),
    ),
    (
        'crafted-belt',
        Item('Sharkskin Belt', 'crafted', 'Bone Winding', ((27, 0, 4), (9, 0, 10 * 256), (105, 0, 5))),
        ('Light Belt', 'Sharkskin Belt', 'Vampirefang Belt'),
        ('27:0', '9:0', '105:0'),
        (),
    ),
)


def cases():
    for slug, original, bases, keys, incidental in EXAMPLES:
        role = 'abyss-warlock-table-glove-belt-' + slug
        for base in bases:
            item = replace(original, base=base)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
                ('unknown-class', item, {}, 'unknown', ()),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
                ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
            ]
            if original.rarity == 'crafted':
                extra = ((39, 0, 30), (41, 0, 30), (43, 0, 30)) + (
                    ((80, 0, 25),) if slug == 'crafted-gloves' else ((99, 0, 24),)
                )
                extra_keys = ('39:0', '41:0', '43:0', '80:0' if slug == 'crafted-gloves' else '99:0')
                rows += [
                    (
                        'affixes',
                        replace(item, raw_stats=item.raw_stats + extra),
                        {'player_class': 'Warlock'},
                        'true',
                        keys + extra_keys,
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
                    id=f'abyss/embedded-gloves-belts/{slug}/{base}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(incidental, (role + '-stats',)),
                    report_contains=(base if original.rarity == 'crafted' else original.name,),
                    evidence=('pricing/data/appraisal-guide-sections.json', 'third-parties/d2data/json/cubemain.json'),
                )


CASES = tuple(cases())
