"""Standard/MF inventory charms: minimum rolls remain useful; Torch class matters."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_unique_charms import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


def cases(
    *,
    build='abyss-warlock-build-guide',
    player_class='Warlock',
    class_id=7,
    variants=None,
    prefix='abyss',
    role_overrides=None,
):
    variants = variants or dict.fromkeys(('gheed', 'annihilus', 'torch'), (1, 2))
    for slug, item, keys in EXAMPLES:
        if slug == 'renewed':
            continue
        if slug == 'torch':
            item = replace(
                item,
                raw_stats=tuple(
                    (stat, class_id if stat == 83 else layer, value) for stat, layer, value in item.raw_stats
                ),
            )
            keys = tuple(f'83:{class_id}' if key == '83:7' else key for key in keys)
        suffix = 'gheeds-inventory' if slug == 'gheed' else slug
        roles = (role_overrides or {}).get(slug, tuple(f'{build}-{variant}-{suffix}' for variant in variants[slug]))
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': player_class}
        rows = [
            ('minimum', item, context, 'true', 'positive', keys),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative', ()),
            (
                'unread-stats',
                replace(item, raw_stats=(), complete=False),
                context,
                'unknown' if slug == 'torch' else 'true',
                'unknown',
                (),
            ),
        ]
        if slug == 'gheed':
            rows += [
                (
                    'perfect',
                    replace(item, raw_stats=((80, 0, 40), (79, 0, 160), (87, 0, 15))),
                    context,
                    'true',
                    'positive',
                    keys,
                ),
                (
                    'discount-unread',
                    replace(item, raw_stats=((80, 0, 20), (79, 0, 80)), complete=False),
                    context,
                    'true',
                    'unknown',
                    ('80:0', '79:0'),
                ),
            ]
        else:
            rows += [
                (
                    'wrong-wearer-class',
                    item,
                    {'player_class': 'Paladin' if player_class == 'Sorceress' else 'Sorceress'},
                    'false',
                    'negative',
                    (),
                ),
                ('unknown-wearer-class', item, {}, 'unknown', 'unknown', ()),
                (
                    'perfect-attributes-resists',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 20 if stat in (0, 1, 2, 3, 39, 41, 43, 45) else value)
                            for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                    'positive',
                    keys,
                ),
            ]
        if slug == 'torch':
            rows += [
                (
                    'different-class-torch',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, (7 if class_id == 1 else 1) if stat == 83 else layer, value)
                            for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'false',
                    'negative',
                    (),
                ),
                (
                    'unread-class-roll',
                    replace(item, raw_stats=item.raw_stats[1:], complete=False),
                    context,
                    'unknown',
                    'unknown',
                    (),
                ),
                (
                    'depleted-hydra',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 10 * 256 if stat == 204 else value) for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                    'positive',
                    keys,
                ),
            ]
        for label, candidate, loadout, truth, scenario, expected_keys in rows:
            expected = {
                'roles': Contains(*[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles])
            }
            if expected_keys:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in expected_keys}
                    )
                )
            yield Case(
                id=f'{prefix}/inventory-charms/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario=scenario,
                absent_configurations=() if expected_keys else configs,
                absent_stat_configurations={
                    **dict.fromkeys(('198:12618', '204:3998', '89:0'), configs),
                    **({'87:0': configs} if label == 'discount-unread' else {}),
                },
                report_contains=(candidate.name, 'Trade tier:') if scenario == 'positive' else (candidate.base,),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
