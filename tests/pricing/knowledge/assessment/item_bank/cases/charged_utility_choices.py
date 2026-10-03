"""Carried/swap charges: active uses, finite ethereal life, and Infinity condition."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('blizzard-sorceress', 'Sorceress', 91, 'Weapon-Swap', 0),
    ('lightning-sorceress', 'Sorceress', 91, 'Weapon-Swap', 0),
    ('fire-warlock-guide', 'Warlock', 91, 'Other', 0),
    ('fissure-druid', 'Druid', 91, 'Other', 0),
    ('lightning-fury-amazon-guide', 'Amazon', 91, 'Weapon-Swap', 0),
    ('lightning-strike-amazon', 'Amazon', 91, 'Weapon-Swap', 1),
    ('fire-warlock-guide', 'Warlock', 54, 'Weapon-Swap', 0),
    ('lightning-fury-amazon-guide', 'Amazon', 54, 'Weapon-Swap', 1),
)


def cases():
    for klass, skill in dict.fromkeys((s[1], s[2]) for s in SPECS):
        specs = tuple(s for s in SPECS if (s[1], s[2]) == (klass, skill))
        roles = tuple(f'{s[0]}-starter-charges-{skill}' for s in specs)
        configs = tuple(role + '-stats' for role in roles)
        base, maximum, suffix, name = (
            ('Bone Wand', 67, 594, 'Lower Resist') if skill == 91 else ('Long Staff', 33, 532, 'Teleport')
        )
        layer = skill * 64 + 1
        key = f'204:{layer}'
        context = {'player_class': klass, 'mercenary_items': []}
        for quality in ('magic', 'rare'):
            item = Item(
                base, quality, raw_stats=((204, layer, maximum * 256 + 1),), affix_records=(('suffix', suffix),)
            )
            examples = [
                ('last-charge', item, context, 'true', 'true'),
                ('full', replace(item, raw_stats=((204, layer, maximum * 257),)), context, 'true', 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'true', 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true', 'true'),
                ('empty', replace(item, raw_stats=((204, layer, maximum * 256),)), context, 'true', 'false'),
                (
                    'empty-ethereal',
                    replace(item, ethereal=True, raw_stats=((204, layer, maximum * 256),)),
                    context,
                    'true',
                    'false',
                ),
                ('unread', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
                ('absent', replace(item, raw_stats=(), affix_records=(), complete=True), context, 'false', 'false'),
                (
                    'invalid-count',
                    replace(item, raw_stats=((204, layer, maximum * 257 + 1),)),
                    context,
                    'unknown',
                    'unknown',
                ),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'false', 'true'),
                ('unknown-class', item, {**context, 'player_class': None}, 'unknown', 'true'),
                ('unidentified', replace(item, identified=False), context, 'true', 'true'),
            ]
            if klass == 'Sorceress':
                examples.extend(
                    [
                        ('infinity', item, {**context, 'mercenary_items': ['Infinity']}, 'true', 'true'),
                        ('unknown-merc', item, {'player_class': klass}, 'true', 'true'),
                    ]
                )
            for label, candidate, loadout, truth, charges in examples:
                active = truth == charges == 'true' and label != 'unidentified'
                active_configs = tuple(
                    config
                    for role, config in zip(roles, configs, strict=True)
                    if active and not (role.startswith('blizzard-') and label in ('infinity', 'unknown-merc'))
                )
                role_checks = []
                for spec, role in zip(specs, roles, strict=True):
                    dependencies = [IsPartialDict(status=charges, trace=IsPartialDict(expected=1))]
                    if role.startswith('blizzard-'):
                        dependencies.append(
                            IsPartialDict(
                                label='The guide recommends this wand when the mercenary does not have Infinity.',
                                status={'infinity': 'false', 'unknown-merc': 'unknown'}.get(label, 'true'),
                            )
                        )
                    role_checks.append(
                        IsPartialDict(
                            id=role,
                            slot=spec[3],
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(*dependencies),
                        )
                    )
                expected = {'roles': Contains(*role_checks)}
                if active_configs:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        *(
                                            IsPartialDict(configuration_id=config, desirability='desirable')
                                            for config in active_configs
                                        )
                                    )
                                ),
                            }
                        )
                    )
                yield Case(
                    id=f'charged-utility-choices/{klass}/{skill}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='unknown'
                    if 'unknown' in (truth, charges) or label == 'unknown-merc'
                    else 'positive'
                    if active_configs and label != 'infinity'
                    else 'negative',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=tuple(config for config in configs if config not in active_configs),
                    report_contains=(name, 'Charges') if active_configs else (),
                    evidence=(
                        *(f'pricing/data/wp-a-builds.json:/{s[0]}/variants/0/player/{s[3]}/{s[4]}' for s in specs),
                        f'third-parties/d2data/json/magicsuffix.json:/{suffix}',
                    ),
                )


CASES = tuple(cases())
