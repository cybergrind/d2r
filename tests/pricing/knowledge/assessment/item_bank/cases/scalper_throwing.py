"""Upgraded Scalper alternatives: exact ethereal variant and quantity sustain."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def weapon(ethereal, damage=150, leech=4):
    # Native unique288: the guide asks for the elite Flying Axe upgrade.
    return Item(
        'Flying Axe',
        'unique',
        'The Scalper',
        (
            (17, 0, damage),
            (18, 0, damage),
            (119, 0, 25),
            (93, 0, 20),
            (135, 0, 33),
            (60, 0, leech),
            (138, 0, 4),
            (253, 0, 30),
        ),
        ethereal=ethereal,
        named_table_id=288,
    )


def cases():
    context = {'player_class': 'Barbarian'}
    for ethereal in (True, False):
        variant = 'ethereal' if ethereal else 'nonethereal'
        other = 'nonethereal' if ethereal else 'ethereal'
        roles = tuple(f'double-throw-scalper-{variant}-{slot}' for slot in ('weapon', 'off-hand'))
        configs = tuple(role + '-stats' for role in roles)
        other_configs = tuple(f'double-throw-scalper-{other}-{slot}-stats' for slot in ('weapon', 'off-hand'))
        item = weapon(ethereal)
        examples = (
            ('minimum', item, context, 'true'),
            ('maximum', weapon(ethereal, 200, 6), context, 'true'),
            ('not-upgraded', replace(item, base='Francisca'), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('socketed', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
            (
                'unread-replenishment',
                replace(item, raw_stats=tuple(row for row in item.raw_stats if row[0] != 253)),
                context,
                'unknown' if ethereal else 'true',
            ),
            (
                'invalid-replenishment',
                replace(item, raw_stats=tuple((s, p, 0 if s == 253 else v) for s, p, v in item.raw_stats)),
                context,
                'unknown' if ethereal else 'true',
            ),
        )
        for label, candidate, loadout, truth in examples:
            active = truth == 'true'
            expected = {}
            if label != 'unidentified':
                expected['roles'] = Contains(
                    *(
                        IsPartialDict(id=role, slot=slot, rule_trace=IsPartialDict(truth=truth))
                        for role, slot in zip(roles, ('Weapon', 'Off-Hand'), strict=True)
                    )
                )
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{stat}:{layer}': IsPartialDict(
                                contributions=Contains(
                                    *(
                                        IsPartialDict(configuration_id=config, desirability='desirable')
                                        for config in configs
                                    )
                                )
                            )
                            for stat, layer, value in candidate.raw_stats
                            if value > 0
                        }
                    )
                )
            yield Case(
                id=f'scalper-throwing/{variant}/{label}',
                item=candidate,
                context=loadout,
                covers=roles,
                report_checks=roll_checks(roles[0], truth, maximum=label == 'maximum')
                if label in ('minimum', 'maximum', 'wrong-class', 'unknown-class')
                else None,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=other_configs + (() if active else configs),
                absent_stat_configurations={'253:0': configs}
                if label in ('unread-replenishment', 'invalid-replenishment')
                else {},
                report_contains=(
                    'The Scalper',
                    'Trade tier:',
                    '(150-200%) Enhanced Damage',
                    '(4-6%) Life stolen per hit',
                )
                if active
                else (),
                evidence=(
                    *(
                        'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots/'
                        f'{slot}/{6 if ethereal else 7}'
                        for slot in ('Weapon', 'Off-Hand')
                    ),
                    'third-parties/d2data/json/uniqueitems.json:/288',
                    'third-parties/d2data/json/weapons.json:/7ta',
                ),
            )


def roll_checks(role, truth, *, maximum):
    quality = 'perfect' if maximum else 'low'
    damage, leech = (200, 6) if maximum else (150, 4)
    stats = []
    for keys, value, low, high, text in (
        (['17:0', '18:0'], damage, 150, 200, f'+{damage}% (150-200%) Enhanced Damage'),
        (['60:0'], leech, 4, 6, f'{leech}% (4-6%) Life stolen per hit'),
    ):
        stats.append(
            {
                'keys': keys,
                'priority': 'desirable',
                'data': {
                    'status': 'decoded',
                    'value': value,
                    'text': text,
                    'roll_range': {'min': low, 'max': high},
                    'roll_tier': None,
                    'roll_quality': quality,
                },
                'body': {'text': text, 'tone': quality},
            }
        )
    for key, value, text in (
        ('119:0', 25, '25% Bonus to Attack Rating'),
        ('93:0', 20, '+20% Increased Attack Speed'),
        ('135:0', 33, '+33% Chance of Open Wounds'),
        ('138:0', 4, '+4 to Mana after each Kill'),
        ('253:0', 30, 'Replenishes quantity'),
    ):
        stats.append(
            {
                'keys': [key],
                'priority': 'desirable',
                'data': {
                    'status': 'decoded',
                    'value': value,
                    'text': text,
                    'roll_range': None,
                    'roll_tier': None,
                    'roll_quality': None,
                },
                'body': {'text': text, 'tone': 'default'},
            }
        )
    return {
        'schema_version': 1,
        'role_id': role,
        'configuration_id': role + '-stats',
        'truth': truth,
        'stats': stats,
    }


CASES = tuple(cases())
