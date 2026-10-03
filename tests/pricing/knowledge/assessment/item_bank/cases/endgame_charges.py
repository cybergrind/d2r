"""Travel and curse charges require available uses and the cited wearer/loadout."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('fissure-druid-ubers-charges-91', 'Druid', 'Bone Wand', 91, 3, 82, 'Lower Resist'),
    ('smite-paladin-standard-travel-staff', 'Paladin', 'Long Staff', 54, 1, 33, 'Teleport'),
)

TRAVEL_USES = (
    ('dragon-talon-assassin-budget-travel-staff', 'Assassin', 'dragon-talon-assassin', 0, 'Other', 0),
    (
        'echoing-strike-warlock-guide-starter-travel-staff',
        'Warlock',
        'echoing-strike-warlock-guide',
        0,
        'Weapon-Swap',
        0,
    ),
    ('fire-blast-assassin-starter-travel-staff', 'Assassin', 'fire-blast-assassin', 0, 'Weapon-Swap', 0),
    ('fissure-druid-starter-travel-staff', 'Druid', 'fissure-druid', 0, 'Weapon-Swap', 0),
    (
        'fist-of-the-heavens-paladin-foh-starter-travel-staff',
        'Paladin',
        'fist-of-the-heavens-paladin',
        0,
        'Weapon-Swap',
        0,
    ),
    (
        'fist-of-the-heavens-paladin-holy-bolt-starter-travel-staff',
        'Paladin',
        'fist-of-the-heavens-paladin',
        1,
        'Weapon-Swap',
        0,
    ),
    ('lightning-sentry-assassin-starter-travel-staff', 'Assassin', 'lightning-sentry-assassin', 0, 'Weapon-Swap', 0),
    ('lightning-strike-amazon-starter-travel-staff', 'Amazon', 'lightning-strike-amazon', 0, 'Weapon-Swap', 1),
    (
        'mirrored-blades-warlock-guide-starter-travel-staff',
        'Warlock',
        'mirrored-blades-warlock-guide',
        0,
        'Weapon-Swap',
        0,
    ),
    ('poison-nova-necromancer-starter-travel-staff', 'Necromancer', 'poison-nova-necromancer', 0, 'Weapon-Swap', 0),
    (
        'summoner-necromancer-guide-starter-travel-staff',
        'Necromancer',
        'summoner-necromancer-guide',
        0,
        'Weapon-Swap',
        0,
    ),
)
TRAVEL_SOURCES = {
    role: f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}/player/{slot}/{index}'
    for role, _, build, variant, slot, index in TRAVEL_USES
}
# Native suffix 532 permits magic/rare staves. At skill level 1 its -30 capacity
# parameter gives 30 + floor(30 / 8) = 33 charges; level 6 would give 52, not 33.
SPECS += tuple((role, klass, 'Long Staff', 54, 1, 33, 'Teleport') for role, klass, *_ in TRAVEL_USES)


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
                ('wrong-class', item, {**context, 'player_class': 'Sorceress'}, 'false', 'true', False),
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
            if role == 'smite-paladin-standard-travel-staff':
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
                    id=f'travel-charges/{role}/{quality}/{label}'
                    if role in TRAVEL_SOURCES
                    else f'endgame-charges/{skill}/{quality}/{label}',
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
                    evidence=(
                        TRAVEL_SOURCES.get(role, 'pricing/data/wp-a-builds.json'),
                        f'third-parties/d2data/json/skills.json:/{skill}',
                        'third-parties/d2data/json/magicsuffix.json:/532'
                        if skill == 54
                        else 'third-parties/d2data/json/magicsuffix.json',
                    ),
                )


CASES = tuple(cases())
