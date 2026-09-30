"""Endgame travel and curse charges require available uses and the cited wearer/loadout."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('fissure-druid-ubers-charges-91', 'Druid', 'Bone Wand', 91, 3, 82, 'Lower Resist'),
    ('smite-paladin-standard-travel-staff', 'Paladin', 'Long Staff', 54, 6, 33, 'Teleport'),
)


def cases():
    for role, wearer, base, skill, level, maximum, name in SPECS:
        context = {'player_class': wearer, **({'player_items': []} if skill == 54 else {})}
        layer = skill * 64 + level
        key = f'204:{layer}'
        for quality in ('magic', 'rare'):
            item = Item(base, quality, raw_stats=((204, layer, (maximum << 8) | 1),))
            rows = [
                ('last-charge', item, context, 'true', 'true', True),
                (
                    'full',
                    replace(item, raw_stats=((204, layer, (maximum << 8) | maximum),)),
                    context,
                    'true',
                    'true',
                    True,
                ),
                ('ethereal-last', replace(item, ethereal=True), context, 'true', 'true', True),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true', 'true', True),
                (
                    'empty-repairable',
                    replace(item, raw_stats=((204, layer, maximum << 8),)),
                    context,
                    'true',
                    'false',
                    False,
                ),
                (
                    'empty-ethereal',
                    replace(item, ethereal=True, raw_stats=((204, layer, maximum << 8),)),
                    context,
                    'true',
                    'false',
                    False,
                ),
                ('unread-charge', replace(item, raw_stats=()), context, 'unknown', 'unknown', False),
                ('known-absent-charge', replace(item, raw_stats=(), complete=True), context, 'false', 'false', False),
                ('wrong-class', item, {**context, 'player_class': 'Amazon'}, 'false', 'true', False),
                ('unknown-class', item, {**context, 'player_class': None}, 'unknown', 'true', False),
                ('unidentified', replace(item, identified=False), context, 'true', 'true', False),
                (
                    'invalid-charge-count',
                    replace(item, raw_stats=((204, layer, (maximum << 8) | (maximum + 1)),)),
                    context,
                    'unknown',
                    'unknown',
                    False,
                ),
            ]
            if skill == 54:
                rows += [
                    ('enigma-equipped', item, {**context, 'player_items': ['Enigma']}, 'true', 'true', False),
                    ('unread-equipment', item, {'player_class': wearer}, 'true', 'true', False),
                ]
            for label, candidate, loadout, truth, charge_truth, active in rows:
                expected = {
                    'roles': Contains(
                        IsPartialDict(
                            id=role,
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(IsPartialDict(status=charge_truth, trace=IsPartialDict(expected=1))),
                        )
                    )
                }
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(
                                            configuration_id=role + '-stats',
                                            role_id=role,
                                            desirability='desirable',
                                        )
                                    )
                                )
                            }
                        )
                    )
                yield Case(
                    id=f'endgame-charges/{skill}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario='positive'
                    if active
                    else 'unknown'
                    if 'unknown' in (truth, charge_truth) or label == 'unread-equipment'
                    else 'negative',
                    absent_configurations=() if active else (role + '-stats',),
                    report_contains=(name, 'Charges') if active else (),
                    evidence=('pricing/data/wp-a-builds.json', f'third-parties/d2data/json/skills.json:/{skill}'),
                )


CASES = tuple(cases())
