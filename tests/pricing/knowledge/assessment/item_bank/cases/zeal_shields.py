"""Zeal shield alternatives, independently constructed from native recipe effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


WORDS = (
    (
        'Phoenix',
        4,
        68,
        (
            (17, 0, 350),
            (18, 0, 350),
            (151, 124, 10),
            (143, 0, 15),
            (32, 0, 350),
            (40, 0, 10),
            (42, 0, 5),
            (7, 0, 50 * 256),
        ),
        ('17:0', '18:0', '151:124', '143:0', '32:0', '40:0', '42:0', '7:0'),
    ),
    (
        'Exile',
        4,
        70,
        (
            (151, 104, 13),
            (188, 25, 2),
            (102, 0, 30),
            (16, 0, 220),
            (252, 0, 25),
            (198, 5253, 15),
            (40, 0, 5),
            (44, 0, 5),
            (80, 0, 25),
            (74, 0, 7),
        ),
        ('151:104', '188:25', '102:0', '16:0', '252:0', '198:5253', '40:0', '44:0', '80:0', '74:0'),
    ),
    (
        'Sanctuary',
        3,
        79,
        ((102, 0, 20), (99, 0, 20), (16, 0, 130), (32, 0, 250), (2, 0, 20), (35, 0, 7)),
        ('102:0', '99:0', '16:0', '32:0', '2:0', '35:0'),
    ),
    (
        'Rhyme',
        2,
        80,
        ((102, 0, 40), (153, 0, 1), (80, 0, 25), (79, 0, 50), (27, 0, 15)),
        ('102:0', '153:0', '80:0', '79:0', '27:0'),
    ),
)


def cases():
    result = []
    for name, sockets, span, raw, keys in WORDS:
        role = 'zeal-paladin-' + name.lower() + '-shield-alternative'
        resistance = 77 if name == 'Sanctuary' else 52 if name == 'Rhyme' else 27
        raw += tuple((stat, 0, resistance) for stat in (39, 41, 43, 45))
        keys += ('39:0', '41:0', '43:0', '45:0')
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Sacred Rondache',
                quality,
                name,
                raw,
                ethereal=name == 'Exile',
                sockets=sockets,
                socket_contents='filled',
                runeword=name,
            )
            variants = [
                ('low-rolls', item, {'player_class': 'Paladin'}, 'positive'),
                ('wrong-base', replace(item, base='Phase Blade'), {'player_class': 'Paladin'}, 'negative'),
                ('empty-sockets', replace(item, socket_contents='empty'), {'player_class': 'Paladin'}, 'negative'),
                ('wrong-sockets', replace(item, sockets=1), {'player_class': 'Paladin'}, 'negative'),
                ('unknown-class', item, {}, 'unknown'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Paladin'}, 'unknown'),
            ]
            if name == 'Exile':
                without_repair = tuple(row for row in raw if row[0] != 252)
                variants += [
                    ('nonethereal', replace(item, ethereal=False), {'player_class': 'Paladin'}, 'positive'),
                    ('unknown-repair', replace(item, raw_stats=without_repair), {'player_class': 'Paladin'}, 'unknown'),
                    (
                        'absent-repair',
                        replace(item, raw_stats=without_repair, complete=True),
                        {'player_class': 'Paladin'},
                        'negative',
                    ),
                    ('nonpaladin-shield', replace(item, base='Monarch'), {'player_class': 'Paladin'}, 'negative'),
                ]
            else:
                variants.append(('ethereal', replace(item, ethereal=True), {'player_class': 'Paladin'}, 'negative'))
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
                if label in ('wrong-base', 'nonpaladin-shield'):
                    # Candidate routing excludes incompatible item families before rule tracing.
                    expected = {'family': 'weapon' if label == 'wrong-base' else 'shield'}
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                result.append(
                    Case(
                        id=f'zeal/shields/{name.lower()}/{quality}/{label}',
                        item=candidate,
                        context=context,
                        expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario=scenario,
                        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                        report_contains=(name,),
                        evidence=(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                        ),
                    )
                )
    return tuple(result)


CASES = cases()
