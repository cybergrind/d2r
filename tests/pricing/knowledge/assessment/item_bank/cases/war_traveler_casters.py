"""War Traveler caster farming utility, distinct from attack damage and thorns."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


TABLES = (
    ('Warlock', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        (
            ('fire-wall-sorceress-guide', 30),
            ('frozen-orb-meteor-sorceress', 29),
            ('frozen-orb-sorceress', 29),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Necromancer', (('summoner-necromancer-guide', 33),)),
)


def groups():
    for player_class, sources in TABLES:
        suffix = 'summoner-caster-gear' if player_class == 'Necromancer' else 'caster-core-gear'
        yield (
            player_class,
            tuple(g + '-war-traveler-' + suffix for g, _ in sources),
            True,
            tuple(
                f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{g}.html/sections/{n}'
                for g, n in sources
            ),
        )
    yield (
        'Druid',
        ('fissure-player-standard-war-traveler', 'fissure-player-magic-find-war-traveler'),
        False,
        (
            'pricing/data/wp-a-builds.json:/fissure-druid/variants/1/player/Boots/0',
            'pricing/data/wp-a-builds.json:/fissure-druid/variants/2/player/Boots/0',
        ),
    )


def cases():
    for base in ('Battle Boots', 'Mirrored Boots'):
        item = Item(
            base,
            'unique',
            'War Traveler',
            raw_stats=(
                (80, 0, 30),
                (96, 0, 25),
                (0, 0, 10),
                (3, 0, 10),
                (16, 0, 150),
                (21, 0, 15),
                (22, 0, 25),
                (78, 0, 5),
                (154, 0, 40),
            ),
        )
        for player_class, roles, table, sources in groups():
            context = {'player_class': player_class}
            examples = [
                ('minimum-rolls', item, context, 'true'),
                ('maximum-mf', replace(item, raw_stats=((80, 0, 50), *item.raw_stats[1:])), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if table:
                examples.extend(
                    (
                        ('illegal-socket', replace(item, sockets=1), context, 'false'),
                        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                result = {'assessment': IsPartialDict(**expected)}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))
                                for key in (
                                    ('80:0', '96:0', '0:0', '3:0', '16:0') if table else ('80:0', '96:0', '0:0', '3:0')
                                )
                            }
                        )
                    )
                    result['assessment'] = IsPartialDict(**expected)
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=80, layer=0),
                                roll_range=IsPartialDict(min=30, max=50),
                                roll_quality='perfect' if label == 'maximum-mf' else 'low',
                            )
                        )
                    )
                yield Case(
                    id=f'war-traveler-casters/{base}/{player_class}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    covers=roles,
                    expected=result,
                    absent_stat_configurations=dict.fromkeys(
                        ('21:0', '22:0', '78:0'), tuple(role + '-stats' for role in roles)
                    ),
                    report_contains=('War Traveler', '(30-50%)', 'Trade tier:') if truth == 'true' else (base,),
                    evidence=(*sources, 'third-parties/d2data/json/uniqueitems.json:/240'),
                )


def breakpoint_cases():
    for base in ('Battle Boots', 'Mirrored Boots'):
        item = Item(
            base,
            'unique',
            'War Traveler',
            raw_stats=(
                (80, 0, 30),
                (96, 0, 25),
                (0, 0, 10),
                (3, 0, 10),
                (16, 0, 150),
                (21, 0, 15),
                (22, 0, 25),
                (78, 0, 5),
            ),
        )
        for build, fcr, fhr in (('meteor-sorceress', 105, 60), ('lightning-sorceress', 117, None)):
            role = build.split('-')[0] + '-mf-war-traveler'
            context = {
                'player_class': 'Sorceress',
                'player_total_fcr': fcr,
                'player_items': ["Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication"],
            }
            if fhr is not None:
                context['player_total_fhr'] = fhr
            examples = [
                ('at-breakpoint', item, context, 'true'),
                ('missing-companions', item, dict(context, player_items=[]), 'true'),
                ('unknown-companions', item, {k: v for k, v in context.items() if k != 'player_items'}, 'true'),
                ('perfect-mf', replace(item, raw_stats=((80, 0, 50), *item.raw_stats[1:])), context, 'true'),
                ('below-cast', item, dict(context, player_total_fcr=fcr - 1), 'false'),
                ('unknown-cast', item, {k: v for k, v in context.items() if k != 'player_total_fcr'}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, dict(context, player_class='Paladin'), 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ]
            if fhr is not None:
                examples.extend(
                    (
                        ('below-recovery', item, dict(context, player_total_fhr=fhr - 1), 'false'),
                        (
                            'unknown-recovery',
                            item,
                            {k: v for k, v in context.items() if k != 'player_total_fhr'},
                            'unknown',
                        ),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true' and label not in ('missing-companions', 'unknown-companions'):
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in ('80:0', '96:0', '0:0', '3:0')
                            }
                        )
                    )
                yield Case(
                    id=f'war-traveler-breakpoints/{base}/{build}/{label}',
                    item=candidate,
                    context=loadout,
                    scenario=(
                        'negative'
                        if label == 'missing-companions'
                        else 'unknown'
                        if label == 'unknown-companions'
                        else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth]
                    ),
                    covers=(role,),
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=(role + '-stats',)
                    if label in ('missing-companions', 'unknown-companions')
                    else (),
                    absent_stat_configurations=dict.fromkeys(('21:0', '22:0', '78:0'), (role + '-stats',)),
                    report_contains=('War Traveler', '(30-50%)', 'Trade tier:') if truth == 'true' else (base,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/2',
                        'third-parties/d2data/json/uniqueitems.json:/240',
                    ),
                )


CASES = (*cases(), *breakpoint_cases())
