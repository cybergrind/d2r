"""Helmet alternatives preserve low rolls, native sockets and whole-loadout limits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'shako',
        Item(
            'Shako',
            'unique',
            'Harlequin Crest',
            ((127, 0, 2), (80, 0, 50), (36, 0, 10), (216, 0, 12 * 256), (217, 0, 12 * 256)),
        ),
        ('127:0', '80:0', '36:0', '216:0', '217:0'),
    ),
    (
        'crown',
        Item(
            'Corona',
            'unique',
            'Crown of Ages',
            ((127, 0, 1), (99, 0, 30), (36, 0, 10), (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20)),
            sockets=1,
        ),
        ('127:0', '99:0', '36:0', '39:0'),
    ),
    (
        'lore',
        Item(
            'Cap',
            'normal',
            'Lore',
            ((127, 0, 1), (1, 0, 10), (41, 0, 30), (34, 0, 7), (138, 0, 2)),
            sockets=2,
            socket_contents='filled',
            runeword='Lore',
        ),
        ('127:0', '1:0', '41:0', '34:0', '138:0'),
    ),
)


def cases():
    for slug, original, keys in EXAMPLES:
        role = 'abyss-warlock-table-helmet-' + slug
        for quality in ('normal', 'superior', 'low_quality') if slug == 'lore' else ('unique',):
            item = replace(original, rarity=quality)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
            ]
            if slug == 'lore':
                rows += [
                    ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                    ('circlet', replace(item, base='Circlet'), {'player_class': 'Warlock'}, 'true'),
                ]
            if slug == 'crown':
                rows += [
                    ('two-sockets', replace(item, sockets=2), {'player_class': 'Warlock'}, 'true'),
                    ('zero-sockets', replace(item, sockets=0), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                ]
            if slug == 'shako':
                rows += [
                    ('socketed', replace(item, sockets=1), {'player_class': 'Warlock'}, 'true'),
                    ('unknown-fcr', item, {'player_class': 'Warlock', 'player_total_fcr': None}, 'true'),
                ]
            for label, candidate, ctx, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                if slug == 'shako' and truth == 'true':
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict({'216:0': IsPartialDict(value=120), '217:0': IsPartialDict(value=120)})
                    )
                yield Case(
                    id=f'abyss/helmets/{slug}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    report_contains=(original.name,),
                    evidence=('pricing/data/appraisal-guide-sections.json',),
                )


CASES = tuple(cases())
