"""Abyss table alternatives: parent utility survives without optional jewel payloads."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('rare', Item('Diadem', 'rare', raw_stats=((83, 7, 2), (105, 0, 20))), ('83:7', '105:0')),
    ('magic', Item('Diadem', 'magic', raw_stats=((188, 58, 3), (105, 0, 20))), ('188:58', '105:0')),
    (
        'coven',
        Item(
            'Bone Visage',
            'normal',
            'Coven',
            ((127, 0, 1), (105, 0, 20), (16, 0, 50), (80, 0, 40), (86, 0, 5), (39, 0, 30), (3, 0, 10)),
            sockets=3,
            socket_contents='filled',
            runeword='Coven',
        ),
        ('127:0', '105:0', '80:0', '39:0'),
    ),
    (
        'hellwarden',
        Item(
            'Death Mask',
            'unique',
            "Hellwarden's Will",
            ((127, 0, 1), (105, 0, 20), (358, 0, 5), (93, 0, 20), (333, 0, 5), (138, 0, 6)),
        ),
        ('127:0', '105:0', '358:0', '138:0'),
    ),
    (
        'horazon',
        Item('Demonhead', 'set', "Horazon's Countenance", ((83, 7, 1), (0, 0, 20), (35, 0, 10))),
        ('83:7', '0:0', '35:0'),
    ),
)


def cases():
    for slug, original, keys in EXAMPLES:
        role = 'abyss-warlock-table-embedded-helmet-' + slug
        for quality in ('normal', 'superior', 'low_quality') if slug == 'coven' else (original.rarity,):
            item = replace(original, rarity=quality)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
            ]
            if slug in ('rare', 'magic'):
                rows += [
                    (
                        'missing-skills',
                        replace(item, raw_stats=((105, 0, 20),), complete=True),
                        {'player_class': 'Warlock'},
                        'false',
                    ),
                    (
                        'unknown-skills',
                        replace(item, raw_stats=((105, 0, 20),)),
                        {'player_class': 'Warlock'},
                        'unknown',
                    ),
                    (
                        'slow-cast',
                        replace(item, raw_stats=(item.raw_stats[0], (105, 0, 10))),
                        {'player_class': 'Warlock'},
                        'false',
                    ),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'true'),
                    ('two-sockets', replace(item, sockets=2), {'player_class': 'Warlock'}, 'true'),
                ]
            if slug == 'coven':
                rows += [
                    ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'false'),
                    ('wrong-base', replace(item, base='Demonhead'), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                ]
            for label, candidate, context, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'abyss/embedded-helmets/{slug}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations={'93:0': (role + '-stats',), '333:0': (role + '-stats',)},
                    evidence=('pricing/knowledge/assessment/planning/ABYSS_EMBEDDED_EVIDENCE.json',),
                )


CASES = tuple(cases())
