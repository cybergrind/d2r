"""Independent native low-roll examples for the guide's four unique charms."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ATTRIBUTES_RESISTS = tuple((stat, 0, 10) for stat in (0, 1, 2, 3, 39, 41, 43, 45))
# Native uniqueitems400/properties hit-skill: 5% chance, level10 (the old planner
# reverses those fields). Hydra charges: level30, 10 maximum and remaining.
TORCH_FIXED = ((89, 0, 8), (198, 197 * 64 + 10, 5), (204, 62 * 64 + 30, 10 * 256 + 10))
EXAMPLES = (
    (
        'bone-break',
        'zeal-paladin-bone-break-gear-inventory-charm',
        195,
        Item('Grand Charm', 'unique', 'Bone Break', ((192, 0, 300), (36, 0, -20)), complete=True),
        ('192:0', '36:0'),
    ),
    (
        'gheed',
        'zeal-paladin-gheed-s-fortune-gear-inventory-charm',
        196,
        Item('Grand Charm', 'unique', "Gheed's Fortune", ((80, 0, 20), (79, 0, 80), (87, 0, 10)), complete=True),
        ('80:0', '79:0', '87:0'),
    ),
    (
        'torch',
        'zeal-paladin-hellfire-torch-gear-inventory-charm',
        197,
        Item('Large Charm', 'unique', 'Hellfire Torch', ((83, 3, 3), *ATTRIBUTES_RESISTS, *TORCH_FIXED), complete=True),
        ('83:3', '0:0', '39:0'),
    ),
    (
        'annihilus',
        'zeal-paladin-annihilus-gear-inventory-charm',
        198,
        Item('Small Charm', 'unique', 'Annihilus', ((127, 0, 1), *ATTRIBUTES_RESISTS, (85, 0, 5)), complete=True),
        ('127:0', '0:0', '39:0', '85:0'),
    ),
)


def cases():
    result = []
    for slug, role, span, item, keys in EXAMPLES:
        scenarios = [
            ('low-rolls', 'positive', item, {'player_class': 'Paladin'}),
            ('wrong-class', 'negative', item, {'player_class': 'Sorceress'}),
            ('unknown-class', 'unknown', item, {}),
            ('unidentified', 'negative', replace(item, identified=False), {'player_class': 'Paladin'}),
            ('unknown-ethereal', 'unknown', replace(item, ethereal=None), {'player_class': 'Paladin'}),
        ]
        if slug in ('bone-break', 'torch'):
            scenarios.extend(
                (
                    (
                        'missing-core',
                        'negative',
                        replace(item, raw_stats=item.raw_stats[1:], complete=True),
                        {'player_class': 'Paladin'},
                    ),
                    (
                        'unread-core',
                        'unknown',
                        replace(item, raw_stats=item.raw_stats[1:], complete=False),
                        {'player_class': 'Paladin'},
                    ),
                )
            )
        if slug == 'bone-break':
            scenarios.extend(
                (
                    label,
                    'unknown',
                    replace(item, raw_stats=((192, 0, value), (36, 0, -20))),
                    {'player_class': 'Paladin'},
                )
                for label, value in (('below-native-sunder', 299), ('above-native-sunder', 301))
            )
        if slug == 'torch':
            scenarios.append(
                (
                    'different-class-torch',
                    'negative',
                    replace(item, raw_stats=((83, 1, 3), *ATTRIBUTES_RESISTS, *TORCH_FIXED), complete=True),
                    {'player_class': 'Paladin'},
                )
            )
        for label, scenario, candidate, context in scenarios:
            malformed_sunder = label in ('below-native-sunder', 'above-native-sunder')
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={
                                'positive': 'true',
                                'negative': 'false',
                                'unknown': 'unknown',
                            }[scenario]
                        ),
                    )
                ),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/unique-charms/{slug}/{label}',
                    item=candidate,
                    context=context,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        **({'price_estimate': IsPartialDict(estimate_ist=None)} if malformed_sunder else {}),
                    },
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(candidate.base, 'Unreadable:')
                    if malformed_sunder
                    else (candidate.base, 'Trade tier:')
                    if scenario == 'positive'
                    else (candidate.base,),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
