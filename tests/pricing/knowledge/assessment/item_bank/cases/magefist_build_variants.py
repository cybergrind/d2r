"""Explicit Magefist builds: source breakpoints and the Fissure Ubers upgrade."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.magefist_caster_tables import BASES, gloves
from tests.pricing.knowledge.assessment.item_bank.models import Case


# Independently reviewed WP-A variants: class, fire skill use, full-loadout FCR/FHR.
USES = (
    ('enchant-sorceress', 1, 'Sorceress', True, None, None),
    ('fire-blast-assassin', 1, 'Assassin', True, 102, None),
    ('fire-warlock-guide', 1, 'Warlock', True, None, None),
    ('fissure-druid', 1, 'Druid', True, 99, None),
    ('fissure-druid', 2, 'Druid', True, None, None),
    ('fissure-druid', 3, 'Druid', True, None, None),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', False, 125, None),
    ('fist-of-the-heavens-paladin', 3, 'Paladin', False, 75, 48),
    ('lightning-sentry-assassin', 1, 'Assassin', False, 65, None),
    ('meteor-sorceress', 1, 'Sorceress', True, 63, 60),
    ('meteor-sorceress', 3, 'Sorceress', True, 105, 86),
    ('meteor-sorceress', 4, 'Sorceress', True, 105, 86),
    ('nova-sorceress-guide', 1, 'Sorceress', False, 105, None),
    ('nova-sorceress-guide', 2, 'Sorceress', False, None, None),
    ('nova-sorceress-guide', 3, 'Sorceress', True, None, None),
    ('wake-of-fire-assassin', 1, 'Assassin', True, 102, None),
)


def cases():
    for guide, index, player_class, fire, fcr, fhr in USES:
        role = f'{guide}-{index}-magefist'
        config = role + '-stats'
        elite_required = guide == 'fissure-druid' and index == 3
        context = {'player_class': player_class}
        for field, value in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
            if value is not None:
                context[field] = value
        examples = [
            (
                base,
                gloves(base, defense),
                context,
                'false' if elite_required and base != 'Crusader Gauntlets' else 'true',
            )
            for base, defense in BASES
        ]
        item = gloves('Crusader Gauntlets', 68) if elite_required else gloves('Light Gauntlets', 12)
        examples.extend(
            (
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, dict(context, player_class='Amazon'), 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            )
        )
        for field, value in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
            if value is not None:
                examples.extend(
                    (
                        (field + '-below', item, dict(context, **{field: value - 1}), 'false'),
                        (field + '-unknown', item, {k: v for k, v in context.items() if k != field}, 'unknown'),
                    )
                )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                keys = ['105:0', '27:0'] + (['126:1'] if fire else [])
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            absent = dict.fromkeys(('48:0', '49:0', '16:0', '31:0'), (config,))
            if not fire:
                absent['126:1'] = (config,)
            yield Case(
                id=f'magefist-build-variants/{guide}-{index}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else (config,),
                report_contains=('Magefist', 'Trade tier:') if truth == 'true' else (candidate.base,),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/105',
                    f'pricing/data/wp-a-builds.json:/{guide}/variants/{index}',
                ),
            )


CASES = tuple(cases())
