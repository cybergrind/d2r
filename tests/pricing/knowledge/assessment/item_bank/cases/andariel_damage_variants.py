"""Primary Warlock and Double Throw planners use IAS/enhanced-damage jewels."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


VARIANTS = (
    ('abyss-warlock-build-guide', 'Warlock', 'Act 2 Might', 'gsg0p0l0', 77),
    ('fire-warlock-guide', 'Warlock', 'Act 2 Might', 'vdglw0lu', 41),
    ('double-throw-barbarian-guide', 'Barbarian', 'Act 1 Fire', 'hf91a0li', 25),
)


CONTEXT = {'player_class': 'Necromancer', 'mercenary_type': 'Act 2 Might'}
CHILD = SocketItem('Jewel', ((93, 0, 15), (17, 0, 31), (18, 0, 31)), True)
ITEM = Item(
    'Demonhead',
    'unique',
    "Andariel's Visage",
    ((93, 0, 35), (17, 0, 31), (18, 0, 31), (39, 0, -30), (60, 0, 8), (0, 0, 25), (127, 0, 2), (16, 0, 100)),
    ethereal=True,
    sockets=1,
    socket_contents='filled',
    socket_items=(CHILD,),
    owned_stats=((16, 0, 100),),
)


def cases():
    perfect = replace(CHILD, raw_stats=((93, 0, 15), (17, 0, 40), (18, 0, 40)))
    examples = (
        ('minimum-ruby', ITEM, CONTEXT, 'positive'),
        (
            'perfect-ruby',
            replace(
                ITEM,
                socket_items=(perfect,),
                raw_stats=tuple((sid, layer, 40 if sid in (17, 18) else value) for sid, layer, value in ITEM.raw_stats),
            ),
            CONTEXT,
            'positive',
        ),
        (
            'fire-resistance-ruby',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 30)), True),)),
            CONTEXT,
            'negative',
        ),
        (
            'below-ruby-tier',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (17, 0, 30), (18, 0, 30)), True),)),
            CONTEXT,
            'negative',
        ),
        (
            'missing-max-ed',
            replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (17, 0, 31)), True),)),
            CONTEXT,
            'negative',
        ),
        ('partial-child', replace(ITEM, socket_items=(replace(CHILD, complete=False),)), CONTEXT, 'unknown'),
        ('unread-child', replace(ITEM, socket_items=()), CONTEXT, 'unknown'),
        ('wrong-mercenary', ITEM, {**CONTEXT, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
        ('unknown-mercenary', ITEM, {'player_class': 'Necromancer'}, 'unknown'),
        ('nonethereal', replace(ITEM, ethereal=False), CONTEXT, 'negative'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), CONTEXT, 'unknown'),
    )
    for build, player_class, mercenary, planner, jewel in VARIANTS:
        for variant in (1, 2):
            role = f'{build}-{variant}-merc-andariel-ias-damage'
            config = role + '-stats'
            yield from variant_cases(build, variant, role, config, player_class, mercenary, planner, jewel, examples)


def variant_cases(build, variant, role, config, player_class, mercenary, planner, jewel, examples):
    for label, item, context, scenario in examples:
        context = {**context, 'player_class': player_class}
        if context.get('mercenary_type') == 'Act 2 Might':
            context['mercenary_type'] = mercenary
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=role,
                    side='merc',
                    rule_trace=IsPartialDict(
                        truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                    ),
                )
            )
        }
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('93:0', '17:0', '18:0', '60:0')}
                )
            )
        yield Case(
            id=f'andariel-damage/{build}/{variant}/{label}',
            item=item,
            context=context,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(role,),
            scenario=scenario,
            absent_configurations=() if scenario == 'positive' else (config,),
            absent_stat_configurations={'39:0': (config,)},
            report_contains=("Andariel's Visage", 'Fire Resist -30%', 'Trade tier:'),
            evidence=(
                f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                f'pricing/raw/mr/planners/{planner}.json:/data/planner/items/{jewel}',
                'third-parties/d2data/json/magicprefix.json:/198',
            ),
        )


CASES = tuple(cases())
