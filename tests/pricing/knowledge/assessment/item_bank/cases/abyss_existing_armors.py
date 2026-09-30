"""Existing standalone armor alternatives, independently checked across qualities."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'stealth',
        'abyss-warlock-build-guide-stealth-progression-equipment',
        Item(
            'Quilted Armor',
            'normal',
            'Stealth',
            ((96, 0, 25), (105, 0, 25), (99, 0, 25), (45, 0, 30), (27, 0, 15), (35, 0, 3), (2, 0, 6)),
            sockets=2,
            socket_contents='filled',
            runeword='Stealth',
        ),
        ('96:0', '105:0', '99:0', '45:0', '27:0'),
    ),
    (
        'que-hegan',
        'abyss-warlock-build-guide-que-hegan-s-wisdom-caster-shield-alternative',
        Item(
            'Mage Plate',
            'unique',
            "Que-Hegan's Wisdom",
            ((127, 0, 1), (105, 0, 20), (99, 0, 20), (138, 0, 3), (35, 0, 6), (1, 0, 15), (16, 0, 140)),
        ),
        ('127:0', '105:0', '99:0', '138:0', '35:0', '1:0', '16:0'),
    ),
    (
        'skullder',
        'abyss-warlock-build-guide-skullder-body-armors-utility-alternative',
        Item('Russet Armor', 'unique', "Skullder's Ire", ((127, 0, 1), (240, 0, 10), (35, 0, 10), (252, 0, 20))),
        ('127:0', '240:0', '35:0'),
    ),
    (
        'tal',
        'abyss-warlock-build-guide-tal-rasha-s-guardianship-tal-player-alternative',
        Item(
            'Lacquered Plate',
            'set',
            "Tal Rasha's Guardianship",
            ((80, 0, 88), (35, 0, 15), (39, 0, 40), (41, 0, 40), (43, 0, 40)),
        ),
        ('80:0', '35:0', '39:0', '41:0', '43:0'),
    ),
)


def cases():
    for slug, role, original, keys in EXAMPLES:
        for quality in ('normal', 'superior', 'low_quality') if slug == 'stealth' else (original.rarity,):
            item = replace(original, rarity=quality)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if slug == 'skullder':
                rows += [
                    ('ethereal-repair', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'true'),
                    (
                        'ethereal-no-repair',
                        replace(item, ethereal=True, raw_stats=item.raw_stats[:-1], complete=True),
                        {'player_class': 'Warlock'},
                        'false',
                    ),
                    (
                        'ethereal-unknown-repair',
                        replace(item, ethereal=True, raw_stats=item.raw_stats[:-1]),
                        {'player_class': 'Warlock'},
                        'unknown',
                    ),
                    ('upgraded', replace(item, base='Balrog Skin'), {'player_class': 'Warlock'}, 'true'),
                ]
            else:
                rows += [
                    ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
                ]
            if slug == 'stealth':
                rows += [
                    ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                ]
            if slug == 'que-hegan':
                rows.append(('upgraded', replace(item, base='Archon Plate'), {'player_class': 'Warlock'}, 'true'))
            for label, candidate, context, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                    if slug == 'skullder':
                        expected['facts'] = IsPartialDict(stats=IsPartialDict({'240:0': IsPartialDict(value=100)}))
                yield Case(
                    id=f'abyss/existing-armors/{slug}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations={'105:0': (role + '-stats',)} if slug == 'tal' else {},
                    report_contains=(original.name,) if original.name else (),
                    evidence=('pricing/data/wp-a-builds.json', 'pricing/data/appraisal-guide-sections.json'),
                )


CASES = tuple(cases())
