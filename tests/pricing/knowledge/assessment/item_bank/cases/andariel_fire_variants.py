"""Explicit IAS/fire jewel configurations across caster and mercenary variants."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.poison_andariel_socketed import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


VARIANTS = (
    ('strafe-amazon', 1, 'Amazon', 'Act 2 Might'),
    ('strafe-amazon', 2, 'Amazon', 'Act 2 Might'),
    ('wake-of-fire-assassin', 1, 'Assassin', 'Act 2 Might'),
    ('lightning-sentry-assassin', 1, 'Assassin', 'Act 2 Holy Freeze'),
    ('lightning-sentry-assassin', 2, 'Assassin', 'Act 2 Holy Freeze'),
    ('meteor-sorceress', 1, 'Sorceress', 'Act 2 Might'),
    ('meteor-sorceress', 3, 'Sorceress', 'Act 2 Might'),
    ('lightning-fury-amazon-guide', 1, 'Amazon', 'Act 2 Might'),
    ('lightning-fury-amazon-guide', 2, 'Amazon', 'Act 2 Might'),
    ('fire-blast-assassin', 1, 'Assassin', 'Act 2 Might'),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', 'Act 2 Might'),
    ('blessed-hammer-paladin', 1, 'Paladin', 'Act 2 Holy Freeze'),
    ('blessed-hammer-paladin', 3, 'Paladin', 'Act 2 Holy Freeze'),
    ('mirrored-blades-warlock-guide', 1, 'Warlock', 'Act 2 Might'),
    ('mirrored-blades-warlock-guide', 2, 'Warlock', 'Act 2 Might'),
    ('blizzard-sorceress', 1, 'Sorceress', 'Act 2 Might'),
    ('blizzard-sorceress', 3, 'Sorceress', 'Act 2 Might'),
    ('lightning-sorceress', 1, 'Sorceress', 'Act 2 Might'),
    ('lightning-sorceress', 2, 'Sorceress', 'Act 2 Might'),
)


def cases():
    for build, variant, klass, merc in VARIANTS:
        context = {'player_class': klass, 'mercenary_type': merc}
        role = f'{build}-{variant}-merc-andariel-ias-fire'
        config = role + '-stats'
        examples = (
            ('linked', ITEM, context, 'positive'),
            ('wrong-merc', ITEM, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', ITEM, {'player_class': klass}, 'unknown'),
            ('nonethereal', replace(ITEM, ethereal=False), context, 'negative'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
            ('missing-child', replace(ITEM, socket_items=()), context, 'unknown'),
            ('ral', replace(ITEM, socket_items=(SocketItem('Ral Rune'),)), context, 'negative'),
            (
                'ias-ed',
                replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (17, 0, 40), (18, 0, 40)), True),)),
                context,
                'negative',
            ),
            (
                'fire-29',
                replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15), (39, 0, 29)), True),)),
                context,
                'negative',
            ),
            ('partial-child', replace(ITEM, socket_items=(SocketItem('Jewel', ((93, 0, 15),)),)), context, 'unknown'),
        )
        for label, item, ctx, scenario in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario],
                        ),
                    )
                ),
                'trade_tier': IsPartialDict(status='reviewed'),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('93:0', '60:0', '0:0', '127:0', '39:0')
                        }
                    )
                )
            yield Case(
                id=f'andariel-fire-variants/{build}/{variant}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                report_contains=("Andariel's Visage", 'Trade tier:')
                + (('Mercenary Andariel helmet with IAS/fire-resistance jewel',) if scenario == 'positive' else ()),
                evidence=(f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',),
            )


CASES = tuple(cases())
