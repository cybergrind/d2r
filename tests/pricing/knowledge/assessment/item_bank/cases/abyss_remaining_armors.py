"""Independent native-stat examples for the remaining Abyss armor alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'enigma',
        Item(
            'Mage Plate',
            'normal',
            'Enigma',
            (
                (127, 0, 2),
                (97, 54, 1),
                (96, 0, 45),
                (31, 0, 975),
                (220, 0, 6),
                (240, 0, 8),
                (76, 0, 5),
                (36, 0, 8),
                (86, 0, 14),
            ),
            sockets=3,
            socket_contents='filled',
            runeword='Enigma',
        ),
        ('127:0', '97:54', '96:0', '31:0', '220:0', '240:0', '76:0', '36:0', '86:0'),
    ),
    (
        'coh',
        Item(
            'Archon Plate',
            'normal',
            'Chains of Honor',
            (
                (127, 0, 2),
                (39, 0, 65),
                (41, 0, 65),
                (43, 0, 65),
                (45, 0, 65),
                (16, 0, 70),
                (0, 0, 20),
                (74, 0, 7),
                (36, 0, 8),
                (80, 0, 25),
                (60, 0, 8),
                (121, 0, 200),
                (122, 0, 100),
            ),
            sockets=4,
            socket_contents='filled',
            runeword='Chains of Honor',
        ),
        ('127:0', '39:0', '41:0', '43:0', '45:0', '16:0', '0:0', '74:0', '36:0', '80:0'),
    ),
    (
        'vipermagi',
        Item(
            'Serpentskin Armor',
            'unique',
            'Skin of the Vipermagi',
            (
                (127, 0, 1),
                (105, 0, 30),
                (39, 0, 20),
                (41, 0, 20),
                (43, 0, 20),
                (45, 0, 20),
                (35, 0, 9),
                (16, 0, 120),
            ),
        ),
        ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0', '35:0', '16:0'),
    ),
)


def cases():
    for slug, original, keys in EXAMPLES:
        role = 'abyss-warlock-table-armor-' + slug
        for quality in ('normal', 'superior', 'low_quality') if original.runeword else ('unique',):
            item = replace(original, rarity=quality)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
                ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
            ]
            if original.runeword:
                rows += [
                    ('empty', replace(item, socket_contents='empty'), {'player_class': 'Warlock'}, 'false'),
                    ('wrong-sockets', replace(item, sockets=2), {'player_class': 'Warlock'}, 'false'),
                    ('wrong-base', replace(item, base='Quilted Armor'), {'player_class': 'Warlock'}, 'false'),
                    ('alternative-base', replace(item, base='Dusk Shroud'), {'player_class': 'Warlock'}, 'true'),
                ]
            else:
                rows += [
                    ('upgraded', replace(item, base='Wyrmhide'), {'player_class': 'Warlock'}, 'true'),
                    ('socketed', replace(item, sockets=1), {'player_class': 'Warlock'}, 'true'),
                ]
            for label, candidate, context, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                yield Case(
                    id=f'abyss/remaining-armors/{slug}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(('60:0', '121:0', '122:0'), (role + '-stats',))
                    if slug == 'coh'
                    else {},
                    report_contains=(original.name,),
                    evidence=('pricing/data/appraisal-guide-sections.json',),
                )


CASES = tuple(cases())
