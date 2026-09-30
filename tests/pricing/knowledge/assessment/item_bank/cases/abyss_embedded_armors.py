"""Native armor effects, with planner trigger reversals explicitly corrected."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


EXAMPLES = (
    (
        'authority',
        Item(
            'Mage Plate',
            'normal',
            'Authority',
            (
                (83, 7, 2),
                (99, 0, 20),
                (39, 0, 30),
                (17, 0, 40),
                (18, 0, 40),
                (201, 24778, 2),
                (198, 25551, 10),
                (194, 0, 3),
            ),
            sockets=3,
            socket_contents='filled',
            runeword='Authority',
            socket_items=tuple(SocketItem(name) for name in ('Hel Rune', 'Shael Rune', 'Ral Rune')),
        ),
        ('83:7', '99:0', '39:0'),
    ),
    (
        'dominion',
        Item(
            'Russet Armor',
            'set',
            "Horazon's Dominion",
            ((188, 56, 2), (16, 0, 75), (9, 0, 75 * 256), (39, 0, 15), (41, 0, 15), (43, 0, 15)),
        ),
        ('188:56', '16:0', '9:0', '39:0', '41:0', '43:0'),
    ),
)


def cases():
    for slug, original, keys in EXAMPLES:
        role = 'abyss-warlock-table-embedded-armor-' + slug
        for quality in ('normal', 'superior', 'low_quality') if slug == 'authority' else ('set',):
            item = replace(original, rarity=quality)
            rows = [
                ('minimum', item, {'player_class': 'Warlock'}, 'true'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown'),
            ]
            if slug == 'authority':
                rows += [
                    (
                        'empty',
                        replace(
                            item,
                            socket_contents='empty',
                            socket_items=(),
                            raw_stats=tuple(s for s in item.raw_stats if s[0] != 194),
                        ),
                        {'player_class': 'Warlock'},
                        'false',
                    ),
                    ('wrong-base', replace(item, base='Dusk Shroud'), {'player_class': 'Warlock'}, 'false'),
                    (
                        'unknown-sockets',
                        replace(
                            item,
                            sockets=None,
                            socket_items=(),
                            raw_stats=tuple(s for s in item.raw_stats if s[0] != 194),
                        ),
                        {'player_class': 'Warlock'},
                        'unknown',
                    ),
                ]
            else:
                rows += [
                    ('upgraded', replace(item, base='Balrog Skin'), {'player_class': 'Warlock'}, 'true'),
                    ('socketed', replace(item, sockets=1), {'player_class': 'Warlock'}, 'true'),
                    ('too-many-sockets', replace(item, sockets=2), {'player_class': 'Warlock'}, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), {'player_class': 'Warlock'}, 'unknown'),
                ]
            for label, candidate, context, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in keys}
                        )
                    )
                    if slug == 'dominion':
                        expected['facts'] = IsPartialDict(stats=IsPartialDict({'9:0': IsPartialDict(value=75)}))
                yield Case(
                    id=f'abyss/embedded-armors/{slug}/{quality}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(
                        ('17:0', '18:0', '201:24778', '198:25551'), (role + '-stats',)
                    ),
                    report_contains=(
                        '2% Chance to cast level 10 Psychic Ward when struck',
                        '10% Chance to cast level 15 Miasma Chain on striking',
                        'Hel, Shael, Ral',
                    )
                    if slug == 'authority' and label == 'minimum'
                    else (),
                    evidence=(
                        'pricing/raw/mr/planners/gsg0p0l0.json',
                        'tests/inventory_tracking/fixtures/authority_mage_plate.json',
                    ),
                )


CASES = tuple(cases())
