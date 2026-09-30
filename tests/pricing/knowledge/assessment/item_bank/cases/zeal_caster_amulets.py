"""Separate Zeal caster-craft uses, with actual Teleport availability."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


TELEPORT = (54 << 6) | 3
CORE = ((83, 3, 2), (105, 0, 5), (9, 0, 10 * 256), (27, 0, 4))


def cases():
    result = []
    for slug, span, raw, keys in (
        (
            'teleport',
            154,
            (*CORE, (204, TELEPORT, 1 | (27 << 8)), (60, 0, 6), (7, 0, 41 * 256)),
            ('83:3', '105:0', '9:0', '27:0', f'204:{TELEPORT}', '60:0', '7:0'),
        ),
        (
            'resistance-mf',
            155,
            (*CORE, (80, 0, 21), (39, 0, 16), (41, 0, 16), (43, 0, 16), (45, 0, 16)),
            ('83:3', '105:0', '9:0', '27:0', '80:0', '39:0', '41:0', '43:0', '45:0'),
        ),
        (
            'fast-mf',
            156,
            ((83, 3, 2), (105, 0, 15), (9, 0, 10 * 256), (27, 0, 4), (80, 0, 21)),
            ('83:3', '105:0', '9:0', '27:0', '80:0'),
        ),
    ):
        item = Item('Amulet', 'crafted', raw_stats=raw)
        role = 'zeal-paladin-caster-amulet-' + slug
        context = {'player_class': 'Paladin', 'player_items': []}
        variants = [
            ('positive', 'low-roll', item, context),
            ('negative', 'wrong-class', item, {**context, 'player_class': 'Sorceress'}),
            ('unknown', 'unknown-class', item, {'player_items': []}),
            (
                'negative',
                'missing-fcr',
                replace(item, raw_stats=tuple(s for s in raw if s[0] != 105), complete=True),
                context,
            ),
            ('unknown', 'unread-fcr', replace(item, raw_stats=tuple(s for s in raw if s[0] != 105)), context),
        ]
        if slug == 'teleport':
            variants.extend(
                [
                    ('negative', 'enigma', item, {**context, 'player_items': ['Enigma']}),
                    ('unknown', 'unknown-armor', item, {'player_class': 'Paladin'}),
                    (
                        'negative',
                        'empty-charges',
                        replace(
                            item,
                            raw_stats=tuple(
                                (stat, layer, 27 << 8) if stat == 204 else (stat, layer, value)
                                for stat, layer, value in raw
                            ),
                        ),
                        context,
                    ),
                ]
            )
        for scenario, label, candidate, loadout in variants:
            expected = {'roles': Contains(IsPartialDict(id=role))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id=f'zeal/caster-amulets/{slug}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=('Amulet',),
                    evidence=(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/{span}',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
