"""Goldwrap slot uses preserve caster versus attack/trap stat recipients."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('double-throw-barbarian-guide', 'Barbarian', 3, ('80:0', '93:0')),
    ('dream-paladin', 'Paladin', 5, ('80:0', '93:0')),
    ('echoing-strike-warlock-guide', 'Warlock', 1, ('80:0',)),
    ('fire-blast-assassin', 'Assassin', 1, ('80:0', '93:0')),
    ('fire-warlock-guide', 'Warlock', 1, ('80:0',)),
    ('fissure-druid', 'Druid', 3, ('80:0',)),
    ('fist-of-the-heavens-paladin', 'Paladin', 4, ('80:0',)),
    ('gold-find-barbarian', 'Barbarian', 1, ('80:0', '79:0')),
    ('lightning-sentry-assassin', 'Assassin', 1, ('80:0', '93:0')),
    ('meteor-sorceress', 'Sorceress', 1, ('80:0',)),
    ('mirrored-blades-warlock-guide', 'Warlock', 1, ('80:0', '93:0')),
    ('nova-sorceress-guide', 'Sorceress', 1, ('80:0',)),
    ('strafe-amazon', 'Amazon', 3, ('80:0', '93:0')),
    ('wake-of-fire-assassin', 'Assassin', 1, ('80:0', '93:0')),
)


def cases():
    for base in ('Heavy Belt', 'Battle Belt', 'Troll Belt'):
        item = Item(
            base,
            'unique',
            'Goldwrap',
            raw_stats=(
                (80, 0, 30),
                (79, 0, 50),
                (93, 0, 10),
                (16, 0, 40),
                (31, 0, 25),
                (89, 0, 2),
            ),
        )
        for player_class in dict.fromkeys(row[1] for row in USES):
            uses = [row for row in USES if row[1] == player_class]
            roles = tuple(row[0] + '-goldwrap-find-absorb-alternative' for row in uses)
            context = {'player_class': player_class}
            for label, candidate, loadout, truth in (
                ('minimum-rolls', item, context, 'true'),
                (
                    'maximum-gold-defense',
                    replace(
                        item,
                        raw_stats=(
                            (80, 0, 30),
                            (79, 0, 80),
                            (93, 0, 10),
                            (16, 0, 60),
                            (31, 0, 25),
                            (89, 0, 2),
                        ),
                    ),
                    context,
                    'true',
                ),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Necromancer'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('illegal-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ):
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    configuration_ids=Contains(
                                        *(
                                            g + '-goldwrap-find-absorb-alternative-stats'
                                            for g, _, _, keys in uses
                                            if key in keys
                                        )
                                    )
                                )
                                for key in ('80:0', '79:0', '93:0')
                                if any(key in row[3] for row in uses)
                            }
                        )
                    )
                yield Case(
                    id=f'goldwrap-slot-roles/{base}/{player_class}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=roles,
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations={
                        key: tuple(
                            g + '-goldwrap-find-absorb-alternative-stats' for g, _, _, keys in uses if key not in keys
                        )
                        for key in ('93:0', '79:0', '16:0')
                    },
                    report_contains=('Goldwrap', 'Trade tier:') if truth == 'true' else (base,),
                    evidence=(
                        'third-parties/d2data/json/uniqueitems.json:/115',
                        *(f'pricing/data/wp-a-builds.json:/{g}/slots/Belts/{n}' for g, _, n, _ in uses),
                    ),
                )


def farming_cases():
    for base in ('Heavy Belt', 'Battle Belt', 'Troll Belt'):
        item = Item(
            base,
            'unique',
            'Goldwrap',
            raw_stats=(
                (80, 0, 30),
                (79, 0, 50),
                (93, 0, 10),
                (16, 0, 40),
                (31, 0, 25),
                (89, 0, 2),
            ),
        )
        for build, variant, player_class, attack in (
            ('fire-warlock-guide', 2, 'Warlock', False),
            ('gold-find-barbarian', 1, 'Barbarian', True),
            ('gold-find-barbarian', 2, 'Barbarian', False),
            ('gold-find-barbarian', 3, 'Barbarian', True),
        ):
            role = f'{build}-{variant}-goldwrap'
            context = {'player_class': player_class}
            warcry = build == 'gold-find-barbarian' and variant == 2
            if warcry:
                context['player_total_fcr'] = 105
            examples = [
                ('minimum-gold', item, context, 'true'),
                (
                    'maximum-gold',
                    replace(
                        item,
                        raw_stats=tuple(
                            (stat, layer, 80 if stat == 79 else value) for stat, layer, value in item.raw_stats
                        ),
                    ),
                    context,
                    'true',
                ),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, dict(context, player_class='Sorceress'), 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ]
            if warcry:
                examples.extend(
                    (
                        ('below-cast-breakpoint', item, dict(context, player_total_fcr=104), 'false'),
                        ('unknown-cast-total', item, {'player_class': player_class}, 'unknown'),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in (('80:0', '79:0', '93:0') if attack else ('80:0', '79:0'))
                            }
                        )
                    )
                yield Case(
                    id=f'goldwrap-farming/{base}/{role}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=(role,),
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_stat_configurations=dict.fromkeys(
                        ('16:0', '89:0') if attack else ('16:0', '89:0', '93:0'), (role + '-stats',)
                    ),
                    report_contains=('Goldwrap', '(50-80%)', 'Trade tier:') if truth == 'true' else (base,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                        'third-parties/d2data/json/uniqueitems.json:/115',
                    ),
                )


CASES = (*cases(), *farming_cases())
