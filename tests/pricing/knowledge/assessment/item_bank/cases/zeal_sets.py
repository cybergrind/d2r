"""Reviewed Zeal Sigon and Immortal King partial-set alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SIGON = ("Sigon's Visor", "Sigon's Gage", "Sigon's Wrap", "Sigon's Sabot")
IK = ("Immortal King's Forge", "Immortal King's Detail", "Immortal King's Pillar")
SPECS = (
    (SIGON[0], 'Great Helm', 'sigon-s-visor', SIGON, ((9, 0, 30 << 8), (224, 0, 16)), ('9:0',), ('224:0',)),
    (SIGON[1], 'Gauntlets', 'sigon-s-gage', SIGON, ((0, 0, 10), (19, 0, 20), (93, 0, 30)), ('0:0', '19:0'), ('93:0',)),
    (
        SIGON[2],
        'Plated Belt',
        'sigon-s-wrap',
        SIGON,
        ((7, 0, 20 << 8), (39, 0, 20), (214, 0, 16)),
        ('7:0', '39:0'),
        ('214:0',),
    ),
    (
        SIGON[3],
        'Greaves',
        'sigon-s-sabot',
        SIGON,
        ((96, 0, 20), (43, 0, 40), (19, 0, 50), (80, 0, 50)),
        ('96:0', '43:0'),
        ('19:0', '80:0'),
    ),
    (
        IK[0],
        'War Gauntlets',
        'immortal-king-s-forge',
        IK,
        ((0, 0, 20), (2, 0, 20), (93, 0, 25), (31, 0, 228)),
        ('0:0', '2:0', '31:0'),
        ('93:0',),
    ),
    (
        IK[1],
        'War Belt',
        'immortal-king-s-detail',
        IK,
        ((0, 0, 25), (39, 0, 28), (41, 0, 31), (31, 0, 182), (99, 0, 25)),
        ('0:0', '39:0', '41:0', '31:0'),
        ('99:0',),
    ),
    (
        IK[2],
        'War Boots',
        'immortal-king-s-pillar',
        IK,
        ((96, 0, 40), (19, 0, 110), (7, 0, 44 << 8), (80, 0, 25), (188, 32, 2)),
        ('96:0', '19:0', '7:0'),
        ('80:0',),
    ),
)


def cases():
    result = []
    for name, base, slug, members, raw, intrinsic, bonus in SPECS:
        role = slug + '-zeal-combination'
        config = role + '-stats'
        item = Item(base, 'set', name, raw)
        companions = [n for n in members if n != name]
        scenarios = [
            ('positive', {'player_class': 'Paladin', 'player_items': companions}, item, (*intrinsic, *bonus)),
            ('negative', {'player_class': 'Paladin', 'player_items': [name, name]}, item, ()),
            ('unknown', {'player_class': 'Paladin'}, item, ()),
            ('wrong-class', {'player_class': 'Barbarian', 'player_items': companions}, item, ()),
            (
                'uncaptured-bonus',
                {'player_class': 'Paladin', 'player_items': companions},
                replace(item, raw_stats=tuple(r for r in raw if f'{r[0]}:{r[1]}' not in bonus)),
                intrinsic,
            ),
        ]
        # Repeated copies of one companion still make only two distinct pieces.
        if name in (SIGON[3], IK[0], IK[1], IK[2]):
            two_piece_keys = {
                SIGON[3]: (*intrinsic, '19:0'),
                IK[0]: (*intrinsic, '93:0'),
                IK[1]: intrinsic,
                IK[2]: (),
            }[name]
            scenarios.append(
                ('two-distinct', {'player_class': 'Paladin', 'player_items': [companions[0]] * 3}, item, two_piece_keys)
            )
        for scenario, context, candidate, keys in scenarios:
            expected = {'roles': Contains(IsPartialDict(id=role, build='zeal-paladin'))}
            if keys:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            forbidden = set(bonus) - set(keys) if keys else set()
            if name == IK[2]:
                forbidden.add('188:32')
            result.append(
                Case(
                    id=f'zeal/sets/{slug}/{scenario}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario if scenario in ('positive', 'negative', 'unknown') else 'negative',
                    absent_configurations=() if keys else (config,),
                    absent_stat_configurations=dict.fromkeys(forbidden, (config,)),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/32',
                        f'third-parties/d2data/json/setitems.json:/{name}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
