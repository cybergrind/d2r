"""Named glove/belt table alternatives and their upgraded bases."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'chance',
        'chance-guards-find-absorb-alternative',
        'Chance Guards',
        ('Chain Gloves', 'Heavy Bracers', 'Vambraces'),
        ((80, 0, 25), (79, 0, 200), (19, 0, 25), (16, 0, 20)),
        ('80:0',),
        ('19:0',),
    ),
    (
        'magefist',
        'magefist-caster-progression-alternative',
        'Magefist',
        ('Light Gauntlets', 'Battle Gauntlets', 'Crusader Gauntlets'),
        ((105, 0, 20), (27, 0, 25), (126, 1, 1), (48, 0, 1), (49, 0, 6), (16, 0, 20)),
        ('105:0', '27:0'),
        ('48:0', '49:0', '126:1'),
    ),
    (
        'goldwrap',
        'goldwrap-find-absorb-alternative',
        'Goldwrap',
        ('Heavy Belt', 'Battle Belt', 'Troll Belt'),
        ((80, 0, 30), (79, 0, 50), (93, 0, 10), (16, 0, 40)),
        ('80:0',),
        ('93:0',),
    ),
)


def cases():
    for slug, suffix, name, bases, raw, important, incidental in EXAMPLES:
        role = 'abyss-warlock-build-guide-' + suffix
        for base in bases:
            item = Item(base, 'unique', name, raw)
            for label, candidate, context, truth in (
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
                ('invalid-socket', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in important}
                        )
                    )
                yield Case(
                    id=f'abyss/existing-gloves-belts/{slug}/{base}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(incidental, (role + '-stats',)),
                    report_contains=(name,),
                    evidence=('pricing/data/wp-a-builds.json', 'pricing/data/appraisal-guide-sections.json'),
                )


CASES = tuple(cases())
