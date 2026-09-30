"""Renewed Black Cleft keeps observed modifiers separate from unverified generator bounds."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = tuple(
    'abyss-warlock-build-guide-renewed-black-cleft-' + variant + '-renewed-sunder'
    for variant in ('standard', 'magic-find')
)
ITEM = Item('Crafted Sunder Charm', 'unique', 'Renewed Black Cleft', ((193, 0, 300), (37, 0, -45)))


def cases(roles=ROLES, player_class='Warlock', prefix='abyss'):
    context = {'player_class': player_class}
    configs = tuple(role + '-stats' for role in roles)
    for label, item, loadout, scenario, keys in (
        ('core-only', ITEM, context, 'positive', ('193:0',)),
        (
            'observed-guide-rolls',
            replace(
                ITEM, raw_stats=(*ITEM.raw_stats, (358, 0, 10), (99, 0, 24), (7, 0, 65 * 256), (35, 0, 10), (80, 0, 25))
            ),
            context,
            'positive',
            ('193:0', '358:0', '99:0', '7:0', '35:0', '80:0'),
        ),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'negative', ()),
        ('unknown-class', ITEM, {}, 'unknown', ()),
        ('unread-core', replace(ITEM, raw_stats=((37, 0, -45),)), context, 'unknown', ()),
        ('malformed-core', replace(ITEM, raw_stats=((193, 0, 299), (37, 0, -45))), context, 'negative', ()),
        ('unidentified', replace(ITEM, identified=False), context, 'negative', ()),
        ('socketed', replace(ITEM, sockets=1), context, 'negative', ()),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown', ()),
        (
            'original',
            Item('Grand Charm', 'unique', 'Black Cleft', ((193, 0, 300), (37, 0, -45))),
            context,
            'negative',
            (),
        ),
    ):
        expected = {'price_estimate': IsPartialDict(estimate_ist=None)}
        if scenario == 'positive':
            expected['assessment'] = IsPartialDict(
                roles=Contains(*[IsPartialDict(id=role, rule_trace=IsPartialDict(truth='true')) for role in roles]),
                stat_evaluation=IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                ),
            )
        yield Case(
            id=prefix + '/renewed-sunder/' + label,
            item=item,
            context=loadout,
            expected=expected,
            covers=roles,
            scenario=scenario,
            absent_configurations=() if scenario == 'positive' else configs,
            report_contains=(item.name,),
            evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
        )


CASES = tuple(cases())
