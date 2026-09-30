"""Named shield and swap uses preserve active-set and charge availability limits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CONTEXT = {'player_class': 'Warlock', 'player_level': 80, 'player_strength': 150, 'player_dexterity': 100}
LIDLESS = Item(
    'Grim Shield',
    'unique',
    'Lidless Wall',
    ((127, 0, 1), (105, 0, 20), (77, 0, 10), (1, 0, 10), (138, 0, 3), (16, 0, 80)),
)
EXAMPLES = (
    ('lidless-main', 24, LIDLESS, 'Troll Nest', ('127:0', '105:0', '77:0', '1:0', '138:0'), ()),
    ('lidless-swap', 35, LIDLESS, 'Troll Nest', ('127:0',), ('105:0', '77:0', '1:0', '138:0')),
    (
        'ali-baba',
        30,
        Item(
            'Tulwar',
            'unique',
            'Blade of Ali Baba',
            ((240, 0, 8), (239, 0, 20), (17, 0, 60), (18, 0, 60), (2, 0, 5), (9, 0, 15 * 256)),
            sockets=2,
        ),
        'Hydra Edge',
        ('240:0', '239:0'),
        ('17:0', '18:0'),
    ),
    (
        'gull',
        31,
        Item('Dagger', 'unique', 'Gull', ((80, 0, 100), (9, 0, -5 * 256), (21, 0, 1), (22, 0, 15))),
        'Bone Knife',
        ('80:0',),
        ('9:0', '21:0', '22:0'),
    ),
    (
        'naj',
        32,
        Item('Elder Staff', 'set', "Naj's Puzzler", ((204, 3467, 1 | (69 << 8)), (105, 0, 30), (127, 0, 1))),
        None,
        ('204:3467',),
        ('17:0', '18:0'),
    ),
)


def cases():
    for slug, span, item, upgrade, keys, irrelevant in EXAMPLES:
        role = 'abyss-warlock-player-named-' + slug
        eth_restricted = slug in ('lidless-main', 'naj')
        rows = [
            ('native-low', item, CONTEXT, 'positive', 'true'),
            ('wrong-class', item, {**CONTEXT, 'player_class': 'Paladin'}, 'negative', 'false'),
            ('unknown-class', item, {k: v for k, v in CONTEXT.items() if k != 'player_class'}, 'unknown', 'unknown'),
            ('unknown-sockets', replace(item, sockets=None), CONTEXT, 'unknown', 'unknown'),
            (
                'ethereal',
                replace(item, ethereal=True),
                CONTEXT,
                'negative' if eth_restricted else 'positive',
                'false' if eth_restricted else 'true',
            ),
            (
                'unknown-ethereal',
                replace(item, ethereal=None),
                CONTEXT,
                'unknown' if eth_restricted else 'positive',
                'unknown' if eth_restricted else 'true',
            ),
        ]
        if upgrade:
            rows.append(('upgraded', replace(item, base=upgrade), CONTEXT, 'positive', 'true'))
        if slug == 'naj':
            rows += [
                ('empty-charges', replace(item, raw_stats=((204, 3467, 69 << 8),)), CONTEXT, 'negative', 'true'),
                ('unknown-charges', replace(item, raw_stats=()), CONTEXT, 'unknown', 'true'),
                ('underlevel', item, {**CONTEXT, 'player_level': 77}, 'negative', 'true'),
                ('unknown-equipment', item, {'player_class': 'Warlock'}, 'unknown', 'true'),
                (
                    'socketed-equipment-unknown',
                    replace(item, sockets=1, socket_contents='filled'),
                    CONTEXT,
                    'unknown',
                    'true',
                ),
            ]
        else:
            rows.append(
                (
                    'wrong-socket-count',
                    replace(item, sockets=3 if slug == 'ali-baba' else 2),
                    CONTEXT,
                    'negative',
                    'false',
                )
            )
        for label, candidate, ctx, scenario, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, side='player', rule_trace=IsPartialDict(truth=truth)))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
                if slug == 'ali-baba':
                    expected['facts'] = IsPartialDict(
                        stats=IsPartialDict({'240:0': IsPartialDict(value=80), '239:0': IsPartialDict(value=200)})
                    )
            yield Case(
                id=f'abyss/named-swaps/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                # Set items cannot be ethereal; an impossible capture must not gain a trade tier.
                report_contains=(item.name,) if slug == 'naj' and label == 'ethereal' else (item.name, 'Trade tier:'),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                ),
            )


CASES = tuple(cases())
