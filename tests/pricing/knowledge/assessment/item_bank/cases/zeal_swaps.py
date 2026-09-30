"""Zeal prebuff and casting swaps; skills do not prove active buffs."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CTA_STATS = ((97, 149, 1), (97, 155, 2), (127, 0, 1), (93, 0, 40), (17, 0, 250), (18, 0, 250))
SPIRIT_STATS = (
    (127, 0, 2),
    (105, 0, 25),
    (99, 0, 55),
    (9, 0, 89 * 256),
    (3, 0, 22),
    (147, 0, 3),
    (32, 0, 250),
    (39, 0, 27),
    (41, 0, 62),
    (43, 0, 62),
    (45, 0, 62),
)


def cases():
    result = []
    for name, base, sockets, raw, span, keys in (
        ('Call to Arms', 'Crystal Sword', 5, CTA_STATS, 81, ('97:149', '97:155', '127:0')),
        (
            'Spirit',
            'Sacred Rondache',
            4,
            SPIRIT_STATS,
            87,
            ('127:0', '105:0', '99:0', '9:0', '3:0', '147:0', '32:0', '39:0', '41:0', '43:0', '45:0'),
        ),
    ):
        slug = name.lower().replace(' ', '-')
        role = 'zeal-paladin-' + slug + '-swap-alternative'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(base, quality, name, raw, sockets=sockets, socket_contents='filled', runeword=name)
            variants = [
                ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'negative'),
                ('unknown-class', item, {}, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('wrong-sockets', replace(item, sockets=1), {'player_class': 'Paladin'}, 'negative'),
            ]
            if name == 'Call to Arms':
                no_bo = tuple(row for row in raw if row[:2] != (97, 149))
                variants += [
                    ('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'positive'),
                    ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Paladin'}, 'positive'),
                    ('two-handed', replace(item, base='War Scythe'), {'player_class': 'Paladin'}, 'positive'),
                    ('unknown-bo', replace(item, raw_stats=no_bo), {'player_class': 'Paladin'}, 'unknown'),
                    (
                        'absent-bo',
                        replace(item, raw_stats=no_bo, complete=True),
                        {'player_class': 'Paladin'},
                        'negative',
                    ),
                    (
                        'below-native-bc',
                        replace(item, raw_stats=((97, 149, 1), (97, 155, 1), (127, 0, 1))),
                        {'player_class': 'Paladin'},
                        'negative',
                    ),
                ]
            else:
                variants += [
                    ('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'negative'),
                    ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Paladin'}, 'unknown'),
                    ('sword-variant', replace(item, base='Crystal Sword'), {'player_class': 'Paladin'}, 'negative'),
                    (
                        'ordinary-shield',
                        replace(
                            item,
                            base='Monarch',
                            raw_stats=tuple(
                                (stat, layer, 35 if stat in (41, 43, 45) else value)
                                for stat, layer, value in raw
                                if stat != 39
                            ),
                        ),
                        {'player_class': 'Paladin'},
                        'positive',
                    ),
                ]
            for label, candidate, context, scenario in variants:
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(
                                truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                            ),
                        )
                    )
                }
                if label == 'sword-variant':
                    expected = {'family': 'weapon'}
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in keys
                                if label != 'ordinary-shield' or key != '39:0'
                            }
                        )
                    )
                result.append(
                    Case(
                        id=f'zeal/swaps/{slug}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        absent_stat_configurations=dict.fromkeys(('93:0', '17:0', '18:0'), (role + '-stats',))
                        if name == 'Call to Arms'
                        else {},
                        report_contains=(name,),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
