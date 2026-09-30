"""Completed armor recipe examples, with actual native proc/roll encodings."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RES25 = tuple((s, 0, 25) for s in (39, 41, 43, 45))
TREACHERY = ((93, 0, 45), (99, 0, 20), (43, 0, 30), (79, 0, 50), (201, 17103, 5), (198, 17807, 25), (83, 6, 2))
DURESS = (
    (17, 0, 10),
    (18, 0, 10),
    (16, 0, 150),
    (99, 0, 40),
    (135, 0, 33),
    (136, 0, 15),
    (54, 0, 37),
    (55, 0, 133),
    (39, 0, 15),
    (41, 0, 15),
    (43, 0, 45),
    (45, 0, 15),
)
FORTITUDE = (
    (17, 0, 300),
    (18, 0, 300),
    (16, 0, 200),
    (105, 0, 25),
    (201, 3855, 20),
    (114, 0, 12),
    (216, 0, 8 * 256),
    (34, 0, 7),
    (74, 0, 7),
    (42, 0, 5),
    *RES25,
)
EXAMPLES = (
    (
        'treachery-mid',
        219,
        'Treachery',
        'Great Hauberk',
        False,
        3,
        TREACHERY,
        ('93:0', '99:0', '43:0', '201:17103', '198:17807'),
        ('83:6',),
    ),
    (
        'treachery-end',
        226,
        'Treachery',
        'Archon Plate',
        True,
        3,
        TREACHERY,
        ('93:0', '99:0', '43:0', '201:17103', '198:17807'),
        ('83:6',),
    ),
    (
        'duress-mid',
        220,
        'Duress',
        'Great Hauberk',
        False,
        3,
        DURESS,
        ('17:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0'),
        (),
    ),
    (
        'duress-end',
        227,
        'Duress',
        'Great Hauberk',
        True,
        3,
        DURESS,
        ('17:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0'),
        (),
    ),
    (
        'fortitude-end',
        225,
        'Fortitude',
        'Sacred Armor',
        True,
        4,
        FORTITUDE,
        ('17:0', '16:0', '201:3855', '216:0', '34:0', '74:0', '42:0', '39:0'),
        ('105:0', '114:0'),
    ),
)
MIGHT = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}


def cases():
    result = []
    for slug, span, word, base, eth, sockets, stats, keys, irrelevant in EXAMPLES:
        role = 'zeal-paladin-merc-word-' + slug
        item = Item(base, 'normal', word, stats, ethereal=eth, sockets=sockets, socket_contents='filled', runeword=word)
        rows = [
            ('low-rolls', 'positive', item, MIGHT),
            ('superior', 'positive', replace(item, rarity='superior'), MIGHT),
            (
                'superior-wrong-merc',
                'negative',
                replace(item, rarity='superior'),
                {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'},
            ),
            ('superior-unknown-merc', 'unknown', replace(item, rarity='superior'), {'player_class': 'Paladin'}),
            ('wrong-merc', 'negative', item, {**MIGHT, 'mercenary_type': 'Act 5 Frenzy'}),
            ('unknown-merc', 'unknown', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {**MIGHT, 'player_class': 'Sorceress'}),
            ('unknown-sockets', 'unknown', replace(item, sockets=None), MIGHT),
            ('wrong-sockets', 'negative', replace(item, sockets=2), MIGHT),
            ('empty', 'negative', replace(item, socket_contents='empty'), MIGHT),
            ('unread-recipe', 'unknown', replace(item, runeword=None), MIGHT),
            ('different-base', 'negative', replace(item, base='Mage Plate'), MIGHT),
        ]
        if eth:
            rows.extend(
                [
                    ('nonethereal', 'negative', replace(item, ethereal=False), MIGHT),
                    ('unknown-ethereal', 'unknown', replace(item, ethereal=None), MIGHT),
                ]
            )
        else:
            rows.extend(
                [
                    ('ethereal', 'positive', replace(item, ethereal=True), MIGHT),
                    ('unknown-ethereal', 'positive', replace(item, ethereal=None), MIGHT),
                ]
            )
        for label, scenario, candidate, context in rows:
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
            if label == 'different-base':
                expected['roles'] = ~Contains(IsPartialDict(id=role))
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/merc-word/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(word,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        + f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
