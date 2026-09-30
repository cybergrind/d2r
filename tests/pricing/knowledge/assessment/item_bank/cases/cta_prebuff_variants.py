"""Guide-reviewed CTA swaps: native minimum shouts, proper owner, no perfect-roll gate.

wp-a-builds variant tables explicitly pair Spirit with these swaps except the
Blizzard/Meteor MF variants, which describe four-Ist loot shields separately.
"""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_utility_swaps import CTA
from tests.pricing.knowledge.assessment.item_bank.models import Case


GROUPS = (
    (
        'warlock',
        'Warlock',
        True,
        (
            'abyss-standard',
            'abyss-mf',
            'echoing-standard',
            'echoing-mf',
            'echoing-ubers',
            'mirrored-standard',
            'mirrored-ubers',
            'fire-standard',
            'fire-mf',
        ),
    ),
    (
        'sorceress-spirit',
        'Sorceress',
        True,
        (
            'blizzard-set',
            'meteor-standard',
            'meteor-set',
            'lightning-standard',
            'lightning-mf',
        ),
    ),
    ('sorceress-mf', 'Sorceress', False, ('blizzard-mf', 'meteor-mf')),
)


def cases():
    for group, player_class, paired, prefixes in GROUPS:
        roles = tuple(prefix + '-cta-prebuff' for prefix in prefixes)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': player_class, 'player_swap_items': ['Spirit'] if paired else []}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(CTA, rarity=quality)
            rows = [
                ('minimum', item, context, 'positive', 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'positive', 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'positive', 'true'),
                ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'negative', 'false'),
                ('unknown-class', item, {'player_swap_items': context['player_swap_items']}, 'unknown', 'unknown'),
                ('empty', replace(item, socket_contents='empty'), context, 'negative', 'false'),
                ('wrong-count', replace(item, sockets=4), context, 'negative', 'false'),
                (
                    'missing-command',
                    replace(item, raw_stats=((97, 149, 1),), complete=True),
                    context,
                    'negative',
                    'false',
                ),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
                ('wrong-base', replace(item, base='Broad Sword'), context, 'negative', 'false'),
                ('unread-shouts', replace(item, raw_stats=()), context, 'unknown', 'unknown'),
                (
                    'missing-orders',
                    replace(item, raw_stats=((97, 155, 2),), complete=True),
                    context,
                    'negative',
                    'false',
                ),
            ]
            for label, candidate, loadout, scenario, truth in rows:
                expected = {
                    'roles': Contains(
                        *[IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles]
                    )
                }
                if scenario == 'positive':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs))
                                for key in ('97:149', '97:155', '127:0')
                            }
                        )
                    )
                yield Case(
                    id=f'cta-prebuff/{group}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=roles,
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else configs,
                    absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '93:0', '97:146'), configs),
                    evidence=('pricing/data/wp-a-builds.json',),
                )
            if not paired:
                continue
            for label, loadout, dependency in (
                ('missing-spirit', {**context, 'player_swap_items': []}, 'false'),
                ('unknown-spirit', {'player_class': player_class}, 'unknown'),
                ('main-spirit', {**context, 'player_swap_items': [], 'player_items': ['Spirit']}, 'false'),
                ('merc-spirit', {**context, 'player_swap_items': [], 'mercenary_items': ['Spirit']}, 'false'),
            ):
                yield Case(
                    id=f'cta-prebuff/{group}/{quality}/{label}',
                    item=item,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(
                                *[
                                    IsPartialDict(
                                        id=role,
                                        status='partial',
                                        rule_trace=IsPartialDict(truth='true'),
                                        dependencies=Contains(IsPartialDict(status=dependency)),
                                    )
                                    for role in roles
                                ]
                            )
                        )
                    },
                    covers=roles,
                    scenario='unknown' if dependency == 'unknown' else 'negative',
                    absent_configurations=configs,
                    evidence=('pricing/data/wp-a-builds.json',),
                )


CASES = tuple(cases())
