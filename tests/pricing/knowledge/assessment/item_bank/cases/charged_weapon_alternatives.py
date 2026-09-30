"""Reviewed swap utilities distinguish charges, passive skills, and remaining casts."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Independently reviewed Weapon-Swap slots in wp-a-builds; preserve named bases.
SPECS = (
    (
        'Warlock',
        54,
        'Long Staff',
        (('echoing-strike-warlock-guide', 4), ('fire-warlock-guide', 4), ('mirrored-blades-warlock-guide', 4)),
    ),
    ('Barbarian', 54, 'Long Staff', (('double-throw-barbarian-guide', 9),)),
    ('Paladin', 54, 'Battle Staff', (('dream-paladin', 3), ('fist-of-the-heavens-paladin', 3))),
    ('Druid', 54, 'Long Staff', (('fissure-druid', 3),)),
    ('Amazon', 54, 'Long Staff', (('lightning-fury-amazon-guide', 3), ('lightning-strike-amazon', 3))),
    ('Assassin', 54, 'Battle Staff', (('lightning-sentry-assassin', 3), ('wake-of-fire-assassin', 2))),
    ('Necromancer', 54, 'Long Staff', (('poison-nova-necromancer', 2), ('summoner-necromancer-guide', 2))),
    ('Sorceress', 91, 'Bone Wand', (('blizzard-sorceress', 4), ('lightning-sorceress', 4), ('meteor-sorceress', 4))),
    ('Druid', 91, 'Bone Wand', (('fissure-druid', 1),)),
    ('Amazon', 91, 'Bone Wand', (('lightning-fury-amazon-guide', 1), ('lightning-strike-amazon', 1))),
    ('Assassin', 91, 'Bone Wand', (('lightning-sentry-assassin', 2), ('wake-of-fire-assassin', 1))),
    ('Assassin', 82, 'Bone Wand', (('dragon-talon-assassin', 1),)),
    ('Paladin', 82, 'Bone Wand', (('dream-paladin', 4),)),
)
SKILLS = {54: ('Teleport', 6, 33, 532), 82: ('Life Tap', 3, 82, 578), 91: ('Lower Resist', 3, 82, 594)}


def cases():
    for player, skill, base, sources in SPECS:
        name, level, maximum, suffix = SKILLS[skill]
        layer = skill * 64 + level
        roles = tuple(f'{build}-charge-alternative-weapon-swap-{index}' for build, index in sources)
        context = {'player_class': player}
        wrong_player = 'Warlock' if player != 'Warlock' else 'Barbarian'
        for quality in ('magic', 'rare'):
            item = Item(base, quality, raw_stats=((204, layer, (maximum << 8) | 1),), complete=True)
            rows = (
                ('one-charge', item, context, 'true', 'true'),
                (
                    'full-charges',
                    replace(item, raw_stats=((204, layer, (maximum << 8) | maximum),)),
                    context,
                    'true',
                    'true',
                ),
                ('depleted', replace(item, raw_stats=((204, layer, maximum << 8),)), context, 'true', 'false'),
                ('ethereal-one-charge', replace(item, ethereal=True), context, 'true', 'true'),
                (
                    'ethereal-depleted',
                    replace(item, ethereal=True, raw_stats=((204, layer, maximum << 8),)),
                    context,
                    'true',
                    'false',
                ),
                ('passive-skill-only', replace(item, raw_stats=((107, skill, level),)), context, 'false', 'false'),
                ('trigger-only', replace(item, raw_stats=((201, layer, 10),)), context, 'false', 'false'),
                (
                    'wrong-charged-skill',
                    replace(item, raw_stats=((204, (82 if skill != 82 else 91) * 64 + 3, (82 << 8) | 1),)),
                    context,
                    'false',
                    'false',
                ),
                ('missing-skill', replace(item, raw_stats=()), context, 'false', 'false'),
                ('unread-skill', replace(item, raw_stats=(), complete=False), context, 'unknown', 'unknown'),
                ('wrong-class', item, {'player_class': wrong_player}, 'false', 'true'),
                ('unknown-class', item, {}, 'unknown', 'true'),
            )
            for label, candidate, loadout, truth, available in rows:
                yield Case(
                    id=f'charged-weapon-alternative/{player}/{skill}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(
                                *(
                                    IsPartialDict(
                                        id=role,
                                        rule_trace=IsPartialDict(truth=truth),
                                        dependencies=Contains(
                                            IsPartialDict(status=available, trace=IsPartialDict(expected=1))
                                        ),
                                    )
                                    for role in roles
                                )
                            )
                        )
                    },
                    covers=roles,
                    scenario='negative'
                    if available == 'false'
                    else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    report_contains=(base, *((f'Level {level} {name}',) if available == 'true' else ())),
                    evidence=(
                        *(
                            f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon-Swap/{index}'
                            for build, index in sources
                        ),
                        f'third-parties/d2data/json/magicsuffix.json:/{suffix}',
                        f'third-parties/d2data/json/skills.json:/{skill}',
                    ),
                )


def named_base_cases():
    specs = (
        ('fist-of-the-heavens-paladin', 3, 'Paladin', 54, 'Long Staff'),
        ('lightning-sentry-assassin', 3, 'Assassin', 54, 'Long Staff'),
        ('summoner-necromancer-guide', 2, 'Necromancer', 54, 'Battle Staff'),
        ('dream-paladin', 4, 'Paladin', 82, 'Wand'),
    )
    for build, index, player, skill, base in specs:
        _, level, maximum, _ = SKILLS[skill]
        role = f'{build}-charge-alternative-weapon-swap-{index}'
        for quality in ('magic', 'rare'):
            yield Case(
                id=f'charged-weapon-alternative/named-base/{build}/{quality}',
                item=Item(base, quality, raw_stats=((204, skill * 64 + level, (maximum << 8) | 1),), complete=True),
                context={'player_class': player},
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth='false')))
                    )
                },
                covers=(role,),
                scenario='negative',
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon-Swap/{index}',),
            )


CASES = (*cases(), *named_base_cases())
