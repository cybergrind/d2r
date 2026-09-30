"""Standalone Abyss caster gloves and belt, including valid glove upgrades."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'trang',
        Item(
            'Heavy Bracers',
            'set',
            "Trang-Oul's Claws",
            (
                (105, 0, 20),
                (43, 0, 30),
                (31, 0, 67),
                (188, 16, 2),
            ),
        ),
        ('105:0', '43:0', '31:0'),
        ('188:16',),
    ),
    (
        'arachnid',
        Item(
            'Spiderweb Sash',
            'unique',
            'Arachnid Mesh',
            (
                (127, 0, 1),
                (105, 0, 20),
                (77, 0, 5),
                (16, 0, 90),
                (150, 0, 10),
                (204, 17795, 11 << 8 | 11),
            ),
        ),
        ('127:0', '105:0', '77:0', '16:0'),
        ('150:0', '204:17795'),
    ),
)


def cases():
    for slug, original, keys, incidental in EXAMPLES:
        role = 'abyss-warlock-table-' + slug
        bases = ('Heavy Bracers', 'Vambraces') if slug == 'trang' else ('Spiderweb Sash',)
        for base in bases:
            item = replace(original, base=base)
            for label, candidate, context, truth in (
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
                ('invalid-socket', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false'),
                ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                yield Case(
                    id=f'abyss/named-glove-belt/{slug}/{base}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(incidental, (role + '-stats',)),
                    report_contains=(original.name,),
                    evidence=('pricing/data/appraisal-guide-sections.json',),
                )


CASES = tuple(cases())
