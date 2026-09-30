"""Native low-roll melee alternatives, checked through the complete appraisal path."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict, IsStr

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Explicit independently reviewed native inputs, key benefit and qualitative baseline.
SPECS = (
    (
        'Gore Rider',
        'War Boots',
        'gore-rider',
        'melee-accessory',
        0,
        ((136, 0, 15), (135, 0, 10), (141, 0, 15)),
        '136:0',
        'med',
    ),
    ('Goblin Toe', 'Light Plated Boots', 'goblin-toe', 'melee-accessory', 0, ((136, 0, 25),), '136:0', 'low'),
    (
        'War Traveler',
        'Battle Boots',
        'war-traveler',
        'melee-accessory',
        0,
        ((21, 0, 15), (22, 0, 25), (80, 0, 30)),
        '21:0',
        'low',
    ),
    (
        'String of Ears',
        'Demonhide Sash',
        'string-of-ears',
        'melee-accessory',
        0,
        ((60, 0, 6), (36, 0, 10)),
        '60:0',
        'low',
    ),
    (
        "Nosferatu's Coil",
        'Vampirefang Belt',
        'nosferatu-s-coil',
        'melee-accessory',
        0,
        ((60, 0, 5), (93, 0, 10)),
        '93:0',
        'low',
    ),
    (
        "Verdungo's Hearty Cord",
        'Mithril Coil',
        'verdungo-s-hearty-cord',
        'melee-accessory',
        0,
        ((3, 0, 30), (36, 0, 10)),
        '36:0',
        'low',
    ),
    ('Crown of Ages', 'Corona', 'crown-of-ages', 'survival-armor', 1, ((127, 0, 1), (36, 0, 10)), '36:0', 'med'),
    (
        'Vampire Gaze',
        'Grim Helm',
        'vampire-gaze',
        'survival-armor',
        0,
        ((60, 0, 6), (62, 0, 6), (36, 0, 15)),
        '60:0',
        'med',
    ),
    ('Rockstopper', 'Sallet', 'rockstopper', 'survival-armor', 0, ((36, 0, 10), (99, 0, 30)), '99:0', 'low'),
    (
        'Crown of Thieves',
        'Grand Crown',
        'crown-of-thieves',
        'survival-armor',
        0,
        ((60, 0, 9), (39, 0, 33)),
        '60:0',
        'low',
    ),
    (
        'Harlequin Crest',
        'Shako',
        'harlequin-crest',
        'survival-armor',
        0,
        ((127, 0, 2), (36, 0, 10), (80, 0, 50)),
        '127:0',
        'med',
    ),
    ('Shaftstop', 'Mesh Armor', 'shaftstop', 'survival-armor', 0, ((36, 0, 30), (7, 0, 60 << 8)), '36:0', 'low'),
    ("Duriel's Shell", 'Cuirass', 'duriel-s-shell', 'survival-armor', 0, ((153, 0, 1), (43, 0, 50)), '153:0', 'low'),
)


def cases():
    result = []
    for name, base, slug, family, sockets, stats, key, tier in SPECS:
        role = slug + '-zeal-' + family
        item = Item(base, 'unique', name, stats, sockets=sockets)
        for scenario, candidate in [
            ('positive', item),
            ('negative', replace(item, ethereal=True)),
            ('unknown', replace(item, ethereal=None)),
        ]:
            expected = {
                'roles': Contains(IsPartialDict(id=role, build='zeal-paladin')),
                'trade_tier': IsPartialDict(
                    tier=IsStr(regex='^(high|med|low|trash)$'), baseline=IsPartialDict(tier=tier)
                ),
            }
            if scenario == 'negative':
                expected.pop('trade_tier')
                expected['roles'] = Contains(IsPartialDict(id=role, build='zeal-paladin', status='failed'))
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(role + '-stats'))})
                )
            result.append(
                Case(
                    id='zeal/' + slug + '/' + scenario,
                    item=candidate,
                    context={'player_class': 'Paladin'},
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:') if scenario != 'negative' else (name,),
                    evidence=(
                        'pricing/raw/mr/guides__zeal-paladin.html:gear-table',
                        'third-parties/d2data/json/uniqueitems.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
