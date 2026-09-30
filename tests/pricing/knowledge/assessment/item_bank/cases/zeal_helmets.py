"""Zeal helmet alternatives: native low rolls, durability and unknown facts."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Values independently transcribed from native uniqueitems rows344/208/202/206/248.
ROWS = (
    (
        'Crown of Ages',
        'Corona',
        'crown-of-ages',
        96,
        1,
        ((127, 0, 1), (36, 0, 10), (39, 0, 20), (41, 0, 20), (43, 0, 20), (45, 0, 20), (99, 0, 30), (152, 0, 1)),
        ('127:0', '36:0', '39:0', '41:0', '43:0', '45:0', '99:0'),
    ),
    (
        'Vampire Gaze',
        'Grim Helm',
        'vampire-gaze',
        97,
        0,
        ((60, 0, 6), (62, 0, 6), (36, 0, 15), (35, 0, 10)),
        ('60:0', '62:0', '36:0', '35:0'),
    ),
    (
        'Rockstopper',
        'Sallet',
        'rockstopper',
        101,
        0,
        ((36, 0, 10), (39, 0, 20), (41, 0, 20), (43, 0, 20), (99, 0, 30), (3, 0, 15)),
        ('36:0', '39:0', '41:0', '43:0', '99:0', '3:0'),
    ),
    (
        'Crown of Thieves',
        'Grand Crown',
        'crown-of-thieves',
        104,
        0,
        ((2, 0, 25), (60, 0, 9), (7, 0, 50 * 256), (9, 0, 35 * 256), (39, 0, 33), (79, 0, 80)),
        ('2:0', '60:0', '7:0', '9:0', '39:0', '79:0'),
    ),
    (
        'Harlequin Crest',
        'Shako',
        'harlequin-crest',
        100,
        0,
        (
            (127, 0, 2),
            (36, 0, 10),
            (80, 0, 50),
            (0, 0, 2),
            (1, 0, 2),
            (2, 0, 2),
            (3, 0, 2),
            (216, 0, 12 * 256),
            (217, 0, 12 * 256),
        ),
        ('127:0', '36:0', '80:0', '0:0', '1:0', '2:0', '3:0', '216:0', '217:0'),
    ),
)


def cases():
    result = []
    for name, base, slug, span, sockets, raw, keys in ROWS:
        role = slug + '-zeal-survival-armor'
        item = Item(base, 'unique', name, raw, sockets=sockets)
        variants = [
            ('positive', 'native-low-rolls', item, {'player_class': 'Paladin'}),
            ('negative', 'other-class', item, {'player_class': 'Sorceress'}),
            ('unknown', 'unknown-class', item, {}),
        ]
        if name == 'Crown of Ages':
            variants.append(('positive', 'two-sockets', replace(item, sockets=2), {'player_class': 'Paladin'}))
        for scenario, label, observed, context in variants:
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
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/helmets/{slug}/{label}',
                    item=observed,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
