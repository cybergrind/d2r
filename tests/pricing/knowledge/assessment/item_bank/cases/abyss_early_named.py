"""Native low-roll early mercenary equipment and exact unsocketed configuration."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'rockfleece',
        101,
        Item('Field Plate', 'unique', 'Rockfleece', ((16, 0, 100), (36, 0, 10), (34, 0, 5), (0, 0, 5))),
        'Kraken Shell',
        ('36:0', '34:0', '0:0'),
    ),
    (
        'skin-flayed',
        100,
        Item('Demonhide Armor', 'unique', 'Skin of the Flayed One', ((16, 0, 150), (60, 0, 5), (74, 0, 15))),
        'Scarab Husk',
        ('60:0', '74:0'),
    ),
    (
        'face-horror',
        111,
        Item(
            'Mask',
            'unique',
            'The Face of Horror',
            ((0, 0, 20), (39, 0, 10), (41, 0, 10), (43, 0, 10), (45, 0, 10), (122, 0, 50)),
        ),
        'Demonhead',
        ('0:0', '39:0', '41:0', '43:0', '45:0', '122:0'),
    ),
)


def cases():
    context = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    for slug, span, item, upgrade, keys in EXAMPLES:
        role = 'abyss-warlock-merc-early-' + slug
        for label, candidate, ctx, scenario in (
            ('native-low', item, context, 'positive'),
            ('upgraded', replace(item, base=upgrade), context, 'positive'),
            ('ethereal', replace(item, ethereal=True), context, 'positive'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'positive'),
            ('wrong-merc', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative'),
            ('unknown-merc', item, {'player_class': 'Warlock'}, 'unknown'),
            ('socketed', replace(item, sockets=1), context, 'negative'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'abyss/early-named/{slug}/{label}',
                item=candidate,
                context=ctx,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                report_contains=(item.name, 'Trade tier:'),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__abyss-warlock-build-guide.html/item_spans/{span}',
                ),
            )


CASES = tuple(cases())
