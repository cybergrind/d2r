"""Death's glove/belt Zeal pair: wearer, distinct companion and captured bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    result = []
    for name, base, slug, other, raw, intrinsic, bonus in (
        (
            "Death's Hand",
            'Leather Gloves',
            'hand',
            "Death's Guard",
            ((45, 0, 50), (110, 0, 75), (93, 0, 30)),
            ('45:0', '110:0'),
            ('93:0',),
        ),
        (
            "Death's Guard",
            'Demonhide Sash',
            'guard',
            "Death's Hand",
            ((153, 0, 1), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15)),
            ('153:0',),
            ('39:0', '41:0', '43:0', '45:0'),
        ),
    ):
        item = Item(base, 'set', name, raw)
        role = f'death-s-{slug}-zeal-pair'
        config = role + '-stats'
        for scenario, context in (
            ('positive', {'player_class': 'Paladin', 'player_items': [other]}),
            ('negative', {'player_class': 'Paladin', 'player_items': [name, name]}),
            ('unknown', {'player_class': 'Paladin'}),
            ('wrong-wearer', {'player_class': 'Sorceress', 'player_items': [other]}),
            ('uncaptured-bonus', {'player_class': 'Paladin', 'player_items': [other]}),
        ):
            active = scenario in ('positive', 'uncaptured-bonus')
            keys = (*intrinsic, *bonus) if scenario == 'positive' else intrinsic
            expected = {'roles': Contains(IsPartialDict(id=role, build='zeal-paladin'))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            candidate = (
                replace(item, raw_stats=tuple(row for row in raw if f'{row[0]}:{row[1]}' not in bonus))
                if scenario == 'uncaptured-bonus'
                else item
            )
            result.append(
                Case(
                    id=f'zeal/death-pair/{slug}/{scenario}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario if scenario in ('positive', 'negative', 'unknown') else 'negative',
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(bonus, (config,))
                    if scenario == 'uncaptured-bonus'
                    else {},
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        'pricing/raw/mr/guides__zeal-paladin.html:gear-table',
                        'third-parties/d2data/json/setitems.json',
                        'third-parties/d2data/json/sets.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
