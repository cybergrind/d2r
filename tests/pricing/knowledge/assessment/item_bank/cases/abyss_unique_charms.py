"""Abyss table charms preserve class, native immunity core and optional rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ATTRIBUTES_RESISTS = tuple((stat, 0, 10) for stat in (0, 1, 2, 3, 39, 41, 43, 45))
TORCH_UTILITY = ((89, 0, 8), (198, 12618, 5), (204, 3998, 10 * 256 + 10))
EXAMPLES = (
    (
        'renewed',
        Item('Crafted Sunder Charm', 'unique', 'Renewed Black Cleft', ((193, 0, 300), (37, 0, -45)), complete=True),
        ('193:0', '37:0'),
    ),
    (
        'gheed',
        Item('Grand Charm', 'unique', "Gheed's Fortune", ((80, 0, 20), (79, 0, 80), (87, 0, 10)), complete=True),
        ('80:0', '79:0', '87:0'),
    ),
    (
        'torch',
        Item(
            'Large Charm', 'unique', 'Hellfire Torch', ((83, 7, 3), *ATTRIBUTES_RESISTS, *TORCH_UTILITY), complete=True
        ),
        ('83:7', '0:0', '1:0', '2:0', '3:0', '39:0', '41:0', '43:0', '45:0'),
    ),
    (
        'annihilus',
        Item('Small Charm', 'unique', 'Annihilus', ((127, 0, 1), *ATTRIBUTES_RESISTS, (85, 0, 5)), complete=True),
        ('127:0', '0:0', '1:0', '2:0', '3:0', '39:0', '41:0', '43:0', '45:0', '85:0'),
    ),
)


def cases():
    for slug, item, keys in EXAMPLES:
        role = 'abyss-warlock-table-charm-' + slug
        rows = [
            ('minimum', item, {'player_class': 'Warlock'}, 'true', keys),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false', ()),
            ('unknown-class', item, {}, 'unknown', ()),
            ('ethereal', replace(item, ethereal=True), {'player_class': 'Warlock'}, 'false', ()),
            ('unknown-ethereal', replace(item, ethereal=None), {'player_class': 'Warlock'}, 'unknown', ()),
            ('invalid-sockets', replace(item, sockets=1), {'player_class': 'Warlock'}, 'false', ()),
            ('unidentified', replace(item, identified=False), {'player_class': 'Warlock'}, 'false', ()),
        ]
        if slug in ('renewed', 'torch'):
            rows += [
                ('missing-core', replace(item, raw_stats=item.raw_stats[1:]), {'player_class': 'Warlock'}, 'false', ()),
                (
                    'unread-core',
                    replace(item, raw_stats=item.raw_stats[1:], complete=False),
                    {'player_class': 'Warlock'},
                    'unknown',
                    (),
                ),
            ]
        if slug == 'renewed':
            for label, value in (('below-native-core', 299), ('above-native-core', 301)):
                rows.append(
                    (
                        label,
                        replace(item, raw_stats=((193, 0, value), (37, 0, -45))),
                        {'player_class': 'Warlock'},
                        'unknown',
                        (),
                    )
                )
            rows.append(
                (
                    'observed-optional-rolls',
                    replace(
                        item,
                        raw_stats=(
                            *item.raw_stats,
                            (358, 0, 10),
                            (80, 0, 25),
                            (7, 0, 65 * 256),
                            (99, 0, 24),
                            (35, 0, 10),
                        ),
                    ),
                    {'player_class': 'Warlock'},
                    'true',
                    (*keys, '358:0', '80:0', '7:0', '99:0', '35:0'),
                )
            )
        if slug == 'torch':
            rows.append(
                (
                    'other-class-torch',
                    replace(item, raw_stats=((83, 1, 3), *ATTRIBUTES_RESISTS, *TORCH_UTILITY)),
                    {'player_class': 'Warlock'},
                    'false',
                    (),
                )
            )
            rows.append(
                (
                    'depleted-hydra',
                    replace(item, raw_stats=tuple((s, p, 10 * 256 if s == 204 else v) for s, p, v in item.raw_stats)),
                    {'player_class': 'Warlock'},
                    'true',
                    keys,
                )
            )
        for label, candidate, context, truth, expected_keys in rows:
            assessment = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {k: IsPartialDict(configuration_ids=Contains(role + '-stats')) for k in expected_keys}
                    )
                )
            malformed = label in ('below-native-core', 'above-native-core')
            yield Case(
                id=f'abyss/unique-charms/{slug}/{label}',
                item=candidate,
                context=context,
                expected={
                    'assessment': IsPartialDict(**assessment),
                    **({'price_estimate': IsPartialDict(estimate_ist=None)} if malformed else {}),
                },
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(('198:12618', '204:3998', '89:0'), (role + '-stats',)),
                report_contains=(candidate.base, 'Unreadable:')
                if malformed
                else (candidate.base, 'Trade tier:')
                if truth == 'true'
                else (candidate.base,),
                evidence=('pricing/data/appraisal-guide-sections.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
